import argparse
import base64
import json
import os
import sys

extension_mapping = {
    'jpg': 'jpeg'
}


def get_file_extension(file_path):
    _, extension = os.path.splitext(file_path)
    extension = extension[1:] if extension.startswith('.') else extension
    return extension_mapping.get(extension, extension)


class Converter:
    MANIFEST_FILE = 'manifest.json'
    OUTPUT_FILE = 'data.json'
    ID = 'Id'
    NONE = 'None'
    PROJECT = 'Project'
    PACKAGES = 'Packages'
    ASSET = 'Asset'
    IMAGE = 'Image'
    TYPE = 'Type'
    CATEGORY = 'Category'
    PROPERTIES = 'Properties'
    ASSET_REF = 'AssetRef'
    NAME = 'Name'
    OBJECTS = 'Objects'
    FILENAME = 'FileName'
    FILES = 'Files'

    def __init__(self, root_dir):
        self.project = self.NONE
        self.root_dir = root_dir
        self.assets = []

    @staticmethod
    def _read_json(file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f'The file was not found: {file_path}')
        except json.JSONDecodeError as e:
            print(f'Error decoding JSON: {e}')
        except Exception as e:
            print(f'An unexpected error occurred: {e}')
        sys.exit(1)

    def _parse_image(self, obj):
        image_path = os.path.join(self.root_dir, obj[self.ASSET_REF])
        image_extension = get_file_extension(image_path)
        image_props = obj[self.PROPERTIES]
        image_id = image_props[self.ID]
        with open(image_path, 'rb') as image_file:
            base64_string = base64.b64encode(image_file.read()).decode('utf-8')
        self.assets += [{
            'id': image_id,
            'extension': image_extension,
            'base64': base64_string
        }]

    def _parse_objects_file(self, objects_filename):
        objects_path = os.path.join(self.root_dir, objects_filename)
        data = self._read_json(objects_path)
        objects = data[self.OBJECTS]
        for obj in objects:
            if obj.get(self.TYPE) == self.ASSET and obj.get(self.CATEGORY) == self.IMAGE:
                self._parse_image(obj)

    def _parse_package_files(self, package_files):
        self._parse_objects_file(package_files[self.OBJECTS][self.FILENAME])

    def _parse_packages(self, packages):
        for package in packages:
            package_files = package[self.FILES]
            self._parse_package_files(package_files)

    def parse(self):
        manifest_path = os.path.join(self.root_dir, self.MANIFEST_FILE)
        data = self._read_json(manifest_path)
        self.project = data[self.PROJECT][self.NAME]
        packages = data[self.PACKAGES]
        self._parse_packages(packages)

    def save(self):
        with open(self.OUTPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump({'project': self.project, 'assets': self.assets}, f, ensure_ascii=False, indent=2)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('directory', type=str, help='Directory containing the manifest.json file')
    args = parser.parse_args()
    converter = Converter(args.directory)
    converter.parse()
    converter.save()


if __name__ == '__main__':
    main()
