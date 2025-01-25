import os
import subprocess
import sys

from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton, QFileDialog
)

from _winapi import CREATE_NEW_CONSOLE
from convert import convert


class RepoWindow(QWidget):
    def __init__(self):
        super().__init__()

        self.repo_url = 'https://github.com/vladbelousoff/profile.git'
        self.repo_name = self.repo_url.split('/')[-1].replace('.git', '')
        self.repo_path = os.path.join(os.getcwd(), self.repo_name)

        # Set window title
        self.setWindowTitle('Profile Launcher')
        self.setFixedSize(400, 250)

        # Set layout
        layout = QVBoxLayout()

        # Add 'Update Game' button
        update_game_button = QPushButton('Update Game', self)
        update_game_button.clicked.connect(self.update_repo)
        layout.addWidget(update_game_button)

        # Add 'Update Dialogues' button
        update_dialogue_button = QPushButton('Update Dialogues', self)
        update_dialogue_button.clicked.connect(self.update_dialogue)
        layout.addWidget(update_dialogue_button)

        # Add 'Launch' button
        launch_button = QPushButton('Launch', self)
        launch_button.clicked.connect(self.launch_repo)
        layout.addWidget(launch_button)

        # Add 'Submit Changes' button
        submit_button = QPushButton('Submit Changes', self)
        submit_button.clicked.connect(self.submit_changes)
        layout.addWidget(submit_button)

        # Set the layout to the window
        self.setLayout(layout)

    @staticmethod
    def run_command(command, cwd=None):
        """Run a shell command and print the output."""
        try:
            subprocess.run(
                command,
                check=True,
                stdout=None,
                stderr=None,
                cwd=cwd,
                text=True,
                creationflags=CREATE_NEW_CONSOLE
            )
        except subprocess.CalledProcessError as e:
            print(f'Error running command {" ".join(command)}: {e.stderr}')

    def update_repo(self):
        if os.path.exists(self.repo_path):
            print(f'Pulling changes for repo in {self.repo_path}...')
            self.run_command(['git', '-C', self.repo_path, 'reset', '--hard'])
            self.run_command(['git', '-C', self.repo_path, 'pull'])
        else:
            print(f'Cloning repo from {self.repo_url} into {self.repo_path}...')
            self.run_command(['git', 'clone', self.repo_url, self.repo_path])

        self.run_command(['npm.cmd', 'install'], cwd=self.repo_path)

    def update_dialogue(self):
        dialogue_directory = QFileDialog.getExistingDirectory(self, "Select Dialogue Directory", self.repo_path)

        if dialogue_directory:
            print(f'Updating dialogues in {dialogue_directory}...')
            convert(dialogue_directory, os.path.join(self.repo_path, 'assets', 'data.json'))
        else:
            print('No directory selected.')

    def submit_changes(self):
        data_json_path = os.path.join(self.repo_path, 'assets', 'data.json')

        if os.path.exists(data_json_path):
            print('Submitting changes...')
            self.run_command(['git', '-C', self.repo_path, 'add', data_json_path])
            self.run_command(['git', '-C', self.repo_path, 'commit', '-m', 'Update data.json'])

            # Pull with rebase before pushing
            try:
                self.run_command(['git', '-C', self.repo_path, 'pull', '--rebase'])
                self.run_command(['git', '-C', self.repo_path, 'push'])
            except subprocess.CalledProcessError:
                print('Rebase failed. Please resolve conflicts and try again.')
        else:
            print(f'{data_json_path} does not exist. Please update dialogues first.')

    def launch_repo(self):
        self.run_command(['npm.cmd', 'run', 'start'], cwd=self.repo_path)


if __name__ == '__main__':
    app = QApplication(sys.argv)

    # Create and show the window
    window = RepoWindow()
    window.show()

    sys.exit(app.exec())
