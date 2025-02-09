import argparse
import base64
import json
import os
import sys

from model import *

extension_mapping = {
    'jpg': 'jpeg'
}


def get_file_extension(file_path):
    _, extension = os.path.splitext(file_path)
    extension = extension.lower()
    extension = extension[1:] if extension.startswith('.') else extension
    return extension_mapping.get(extension, extension)


class Converter:
    MANIFEST_FILE = 'manifest.json'
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
    TEXT = 'Text'
    TEXTS = 'Texts'
    ENTITY = 'Entity'
    DISPLAY_NAME = 'DisplayName'
    PREVIEW_IMAGE = 'PreviewImage'
    DIALOGUE = 'Dialogue'
    SIZE = 'Size'
    DIALOGUE_FRAGMENT = 'DialogueFragment'
    PARENT = 'Parent'
    SPEAKER = 'Speaker'
    OUTPUT_PINS = 'OutputPins'
    CONNECTIONS = 'Connections'
    TARGET = 'Target'
    FLOW_FRAGMENT = 'FlowFragment'
    ATTACHMENTS = 'Attachments'

    def __init__(self, root_dir):
        self.project = self.NONE
        self.root_dir = root_dir
        self.images = {}
        self.entities = {}
        self.dialogues = []
        self.fragments = {}
        self.localization = {}

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

    @staticmethod
    def _read_as_base64(file_path):
        try:
            with open(file_path, 'rb') as image_file:
                return base64.b64encode(image_file.read()).decode('utf-8')
        except FileNotFoundError:
            print(f'The file was not found: {file_path}')
        except Exception as e:
            print(f'An unexpected error occurred: {e}')
        sys.exit(1)

    def _parse_image(self, obj):
        image_path = os.path.join(self.root_dir, obj[self.ASSET_REF])
        image_extension = get_file_extension(image_path)
        image_props = obj[self.PROPERTIES]
        image_id = image_props[self.ID]
        image_width = image_props[self.SIZE]['w']
        image_height = image_props[self.SIZE]['h']
        base64_string = self._read_as_base64(image_path)
        self.images[image_id] = {
            'width': image_width,
            'height': image_height,
            'uri': f'data:image/{image_extension};base64,{base64_string}',
        }

    def _parse_entity(self, obj):
        props = obj[self.PROPERTIES]
        self.entities[props[self.ID]] = {
            'name': props[self.DISPLAY_NAME],
            'preview': props[self.PREVIEW_IMAGE][self.ASSET],
        }

    def _parse_dialogue(self, obj):
        props = obj[self.PROPERTIES]
        self.dialogues.append({
            'id': props[self.ID],
            'name': props[self.DISPLAY_NAME],
            'speakers': [],
        })

    def _parse_dialogue_fragment(self, obj):
        props = obj[self.PROPERTIES]
        outputs = []
        for output_pin in props[self.OUTPUT_PINS]:
            if self.CONNECTIONS not in output_pin:
                continue
            for connection in output_pin[self.CONNECTIONS]:
                outputs.append(connection[self.TARGET])

        fragment = {
            'dialogue': props[self.PARENT],
            'text': props[self.TEXT],
            'outputs': outputs,
            # It will be filled in _update_dialogue_fragments
            'inputs': [],
        }

        speaker = props.get(self.SPEAKER)
        if speaker:
            fragment['speaker'] = speaker

        attachments = props.get(self.ATTACHMENTS)
        if attachments:
            fragment['attachments'] = attachments

        self.fragments[props[self.ID]] = fragment
        # Fill speakers for the dialogue
        for dialogue in self.dialogues:
            if dialogue['id'] != props[self.PARENT]:
                continue
            if props[self.SPEAKER] in dialogue['speakers']:
                continue
            dialogue['speakers'].append(props[self.SPEAKER])

    def _parse_flow_fragment(self, obj):
        self._parse_dialogue_fragment(obj)

    def _parse_objects_file(self, objects_filename):
        objects_path = os.path.join(self.root_dir, objects_filename)
        data = self._read_json(objects_path)
        objects = data[self.OBJECTS]
        for obj in objects:
            if obj.get(self.TYPE) == self.ASSET and obj.get(self.CATEGORY) == self.IMAGE:
                self._parse_image(obj)
            if obj.get(self.TYPE) == self.ENTITY:
                self._parse_entity(obj)
            if obj.get(self.TYPE) == self.DIALOGUE:
                self._parse_dialogue(obj)
            if obj.get(self.TYPE) == self.DIALOGUE_FRAGMENT:
                self._parse_dialogue_fragment(obj)
            if obj.get(self.TYPE) == self.FLOW_FRAGMENT:
                self._parse_flow_fragment(obj)

    def _parse_localization(self, localization_filename):
        localization_path = os.path.join(self.root_dir, localization_filename)
        data = self._read_json(localization_path)
        for localization_key, localization in data.items():
            localization_val = {
                # Lower all keys
                key: {k.lower(): v for k, v in val.items()}
                # Filter only entries with self.TEXT in val
                for key, val in localization.items() if self.TEXT in val
            }
            self.localization[localization_key] = localization_val

    def _parse_package_files(self, package_files):
        self._parse_objects_file(package_files[self.OBJECTS][self.FILENAME])
        self._parse_localization(package_files[self.TEXTS][self.FILENAME])

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

    def _update_dialogue_fragments(self):
        # Clear incorrect outputs that don't exist as keys in the dict
        for fragment_id, fragment in self.fragments.items():
            fragment['outputs'] = [x for x in fragment['outputs'] if x in self.fragments]
        # Build inputs based on outputs
        for fragment_id, fragment in self.fragments.items():
            for output in fragment['outputs']:
                self.fragments[output]['inputs'].append(fragment_id)

    """
    Dialogue fragments don't contain information about the speaker by default,
    so we need to check the fragment before to get the speaker name
    """
    def _update_flow_fragments(self):
        for fragment_id, fragment in self.fragments.items():
            if 'speaker' in fragment:
                continue
            for _input in fragment['inputs']:
                speaker = self.fragments[_input].get('speaker')
                if speaker:
                    fragment['speaker'] = speaker
                    break

    def save(self, output_path):
        self._update_dialogue_fragments()
        self._update_flow_fragments()

        assets = {}
        with database.atomic():
            for image_key, image in self.images.items():
                new_image = Asset.create(
                    data=image['uri'],
                    meta=json.dumps({
                        'width': image['width'],
                        'height': image['height'],
                    }))
                assets[image_key] = new_image

        localization = {}
        with database.atomic():
            for loc_key, loc in self.localization.items():
                new_loc = Localization.create(
                    text=loc['']['text'],
                )
                localization[loc_key] = new_loc

        entities = {}
        with database.atomic():
            for entity_key, entity in self.entities.items():
                new_entity = Entity.create(
                    name=localization[entity['name']].id,
                    preview=assets[entity['preview']].id,
                )
                entities[entity_key] = new_entity

        dialogues = {}
        with database.atomic():
            for dialogue in self.dialogues:
                new_dialogue = Dialogue.create(
                    name=localization[dialogue['name']].id,
                )
                dialogues[dialogue['id']] = new_dialogue
                for dialogue_speaker in dialogue['speakers']:
                    DialogueSpeaker.create(
                        dialogue=new_dialogue.id,
                        speaker=entities[dialogue_speaker].id
                    )

        fragments = {}
        with database.atomic():
            for fragment_key, fragment in self.fragments.items():
                if not fragment['dialogue'] in dialogues.keys():
                    continue
                new_fragment = Fragment.create(
                    dialogue=dialogues[fragment['dialogue']].id,
                    speaker=entities[fragment['speaker']].id,
                    text=localization[fragment['text']].id,
                )
                fragments[fragment_key] = new_fragment

        with database.atomic():
            for fragment_key, fragment in self.fragments.items():
                if not fragment['dialogue'] in dialogues.keys():
                    continue
                new_fragment = fragments[fragment_key]
                for output_id in fragment['outputs']:
                    FragmentConnection.create(source=new_fragment.id, target=fragments[output_id].id)
                for input_id in fragment['inputs']:
                    FragmentConnection.create(source=fragments[input_id].id, target=new_fragment.id)

        # JSON saving
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump({
                'project': self.project,
                'localization': self.localization,
                'entities': self.entities,
                'dialogues': self.dialogues,
                'fragments': self.fragments,
                'images': self.images,
            }, f, ensure_ascii=False, indent=2)


def convert(directory, output_path):
    initialize_database()
    converter = Converter(directory)
    converter.parse()
    converter.save(output_path)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'directory',
        type=str,
        nargs='?',  # This makes the argument optional
        default=os.getcwd(),  # Default to current working directory
        help='Directory containing the manifest.json file (default: current directory)'
    )
    args = parser.parse_args()
    print(f"Directory: {args.directory}")
    convert(args.directory, 'data.json')


if __name__ == '__main__':
    main()
