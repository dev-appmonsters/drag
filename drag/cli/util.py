import subprocess
import json
import itertools
import os

def get_git_subtree_hash(dir_name):
    output = subprocess.run(['git', 'rev-parse', '--short=30', "HEAD:{}".format(dir_name)], stdout=subprocess.PIPE)
    if output.returncode != 0:
        raise Exception('Could not get subtree hash of service {}'.format(dir_name))
    return output.stdout.decode('utf-8').strip()

def list_docker_images_with_tags_via_gcloud(repo_base_uri, repo):
    # Its the only workaround with gcloud as of now
    # gcloud container images list-tags asia.gcr.io/xyz-admin/config --format="table[no-heading](tags)"
    repository = "{}/{}".format(repo_base_uri, repo)
    cmd = ['gcloud', 'container', 'images', 'list-tags', repository, '--format="json"']
    output = subprocess.run(cmd, stdout=subprocess.PIPE)
    if output.returncode != 0:
        raise Exception('Could not fetch tags for {} repository'.format(repository))
    containers_list_data = json.loads(output.stdout.decode('utf-8').strip())
    def fetch_tags(element):
        return element['tags']
    tags_from_list_data = [fetch_tags(i) for i in containers_list_data]
    flattened_list_of_tags = [y for x in tags_from_list_data for y in x]
    images_with_tags = [ "{}:{}".format(repository, i) for i in flattened_list_of_tags]
    return images_with_tags

def get_relative_context(context):
    cwd = os.getcwd()
    return context.replace("{}/".format(cwd), '')

def get_directory_name_from_context(context):
    return context.split('/')[-1]
