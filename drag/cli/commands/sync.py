from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals

import logging
import sys
import os
import six
import copy
import operator

import subprocess

from .base import Base
from compose.service import parse_repository_tag
from compose import progress_stream
from compose.progress_stream import stream_output
from compose.progress_stream import StreamOutputError
from compose.errors import OperationFailedError
from compose.project import ProjectError

from docker.errors import ImageNotFound
from docker.errors import NotFound
from docker.utils import version_lt

from drag.cli.util import get_git_subtree_hash, list_docker_images_with_tags_via_gcloud
from drag.cli.util import get_relative_context, get_directory_name_from_context

from compose import parallel

log = logging.getLogger(__name__)

class Sync(Base):
    """
    Pull or build all images defined in docker-compose.yaml

    Usage: sync (--repo=<repo>) [options...] [SERVICES...]

    Options:
        --push                      Push fresh built images.
        --disable-parallel          Disable parallel operations.
    """

    def run(self):
        if not self.options['--repo']:
            log.error('--repo is required and must be a docker repository base url')
        self.docker_registry_base = self.options['--repo']

        services = []
        for service in self.project.get_services_without_duplicate(service_names=self.options['SERVICES']):
            if service.can_be_built():
                services.append(service)
            else:
                log.info('%s uses an image, skipping' % service.name)

        def process_service(service):
            self.process_service(service)

        if not self.options['--disable-parallel']:
            _, errors = parallel.parallel_execute(
                services,
                process_service,
                operator.attrgetter('name'),
                'Syncing',
                limit=5,
            )
            if len(errors):
                combined_errors = '\n'.join([
                    e.decode('utf-8') if isinstance(e, six.binary_type) else e for e in errors.values()
                ])
                raise ProjectError(combined_errors)

        else:
            for service in services:
                process_service(service)

    def process_service(self, service, silent=False):

        if 'image' not in service.options:
            # [Developer] I know its peretty bad hack, I can improve on this by having a clone of this object
            image_with_tag = self.get_repository_name_with_tag(service)
            log.info('Service (%s) docker image should be (%s)' % (service.name, image_with_tag))
            service.options['image'] = image_with_tag

        repo, tag, _ = parse_repository_tag(service.options['image'])
        kwargs = {
            'tag': tag or 'latest',
            'stream': True,
            'platform': getattr(service, 'platform', None),
        }

        if kwargs['platform'] and version_lt(service.client.api_version, '1.35'):
            raise OperationFailedError(
                'Impossible to perform platform-targeted pulls for API version < 1.35'
            )
        self.try_to_pull_otherwise_build(service, repo, kwargs)

    def try_to_pull_otherwise_build(self, service, repo, kwargs):
        docker_image_with_tag = self.get_repository_name_with_tag(service)
        if docker_image_with_tag in list_docker_images_with_tags_via_gcloud(self.docker_registry_base, self.repository_name(service)):
            log.info('Found %s Already present pulling in directly' % (docker_image_with_tag))
            self.pull_from_remote_repository(service, repo, kwargs)
        else:
            log.info('Image not found %s building it on fly' % (docker_image_with_tag))
            service.build()
            if self.options['--push']:
                log.info('Pushing image %s as its freshly built now' % (docker_image_with_tag))
                service.push()

        self.tag_with_latest(service)

    def tag_with_latest(self, service):
        minimal_tag = '{s.name}:latest'.format(s=service)
        project_tag = '{p}_{s.name}:latest'.format(s=service, p=service.project.lstrip('_-'))
        log.info('Tagging %s with (%s)...' % (service.image_name, minimal_tag))
        service.client.tag(service.image_name, minimal_tag)
        log.info('Tagging %s with (%s)...' % (service.image_name, project_tag))
        service.client.tag(service.image_name, project_tag)

    def pull_from_remote_repository(self, service, repo, kwargs):
        log.info('Pulling %s (%s) (%s)...' % (service.name, repo, kwargs))
        try:
            output = service.client.pull(repo, **kwargs)
            return progress_stream.get_digest_from_pull(
                stream_output(output, sys.stdout))
        except (StreamOutputError, NotFound) as e:
            log.error(six.text_type(e))
            raise

    def get_repository_name_with_tag(self, service):
        relative_dir_service = get_relative_context(service.options['build']['context'])
        service_subtree_hash = get_git_subtree_hash(relative_dir_service)
        repo_name = self.repository_name(service)
        if 'common' in service.get_dependency_names():
            common_subtree_hash = get_git_subtree_hash('common')
            return "{}/{}:{}-{}".format(self.docker_registry_base, repo_name, service_subtree_hash, common_subtree_hash)
        return "{}/{}:{}".format(self.docker_registry_base, repo_name, service_subtree_hash)

    def repository_name(self, service):
        return get_directory_name_from_context(get_relative_context(service.options['build']['context']))
