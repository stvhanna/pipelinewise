#!/usr/bin/env python3

import os
from subprocess import Popen, PIPE, STDOUT
import shlex
import logging
import json

LOGGER = logging.getLogger('REST API')

class Manager(object):
    '''...'''
    flows = []

    def __init__(self, config_dir, venv_dir, logger):
        self.logger = logger
        self.config_dir = config_dir
        self.venv_dir = venv_dir
        self.etlwise_bin = os.path.join(self.venv_dir, "cli", "bin", "etlwise")
        self.config_path = os.path.join(self.config_dir, "config.json")
        self.load_config()
    
    def load_json(self, file):
        try:
            self.logger.info('Parsing file at {}'.format(file))
            if os.path.isfile(file):
                with open(file) as f:
                    return json.load(f)
            else:
                return None
        except Exception as exc:
            raise Exception("Error parsing {} {}".format(file, exc))

    def save_json(self, data, file):
        try:
            self.logger.info("Saving file {}".format(file))
            with open(file, 'w') as f:
                return json.dump(data, f, indent=2, sort_keys=True)
        except Exception as exc:
            raise Exception("Cannot save to JSON {} {}".format(file), exc)
 
    def load_config(self):
        self.logger.info('Loading config at {}'.format(self.config_path))
        self.config = self.load_json(self.config_path)

    def run_command(self, command, polling=False):
        self.logger.debug('Running command with polling [{}] : {} with'.format(polling, command))

        if polling:
            proc = Popen(shlex.split(command), stdout=PIPE, stderr=STDOUT)
            stdout = ''
            while True:
                line = proc.stdout.readline()
                if proc.poll() is not None:
                    break
                if line:
                    stdout += line.decode('utf-8')

            rc = proc.poll()
            if rc != 0:
                self.logger.error(stdout)

            return { 'stdout': stdout, 'stderr': None, 'returncode': rc }

        else:
            proc = Popen(shlex.split(command), stdout=PIPE, stderr=PIPE)
            x = proc.communicate()
            rc = proc.returncode
            stdout = x[0].decode('utf-8')
            stderr = x[1].decode('utf-8')

            if rc != 0:
              self.logger.error(stderr)

            return { 'stdout': stdout, 'stderr': stderr, 'returncode': rc }

    def get_tap_dir(self, target_id, tap_id):
        return os.path.join(self.config_dir, target_id, tap_id)

    def get_tap_log_dir(self, target_id, tap_id):
        return os.path.join(self.get_tap_dir(target_id, tap_id), 'log')
    
    def parse_connector_files(self, connector_dir):
        name = os.path.basename(connector_dir)

        return {
            'config': self.load_json(os.path.join(connector_dir, 'config.json')),
            'properties': self.load_json(os.path.join(connector_dir, 'properties.json')),
            'state': self.load_json(os.path.join(connector_dir, 'state.json')),
        }
    
    def get_config(self):
        self.load_config()
        return self.config 
    
    def get_targets(self):
        self.logger.info('Getting targets from {}'.format(self.config_path))
        self.load_config()
        try:
            targets = self.config['targets']
        except Exception as exc:
            raise Exception("Targets not defined")

        return targets

    def get_target(self, target_id):
        self.logger.info('Getting {} target'.format(target_id))
        targets = self.get_targets()

        target = False
        target = next((item for item in targets if item["id"] == target_id), False)
        
        if target == False:
            raise Exception("Cannot find {} target".format(target_id))

        return target
    
    def get_taps(self, target_id):
        self.logger.info('Getting taps from {} target'.format(target_id))
        target = self.get_target(target_id)

        try:
            taps = target['taps']
        except Exception as exc:
            raise Exception("No taps defined for {} target".format(target_id))
        
        return taps
    
    def get_tap(self, target_id, tap_id):
        self.logger.info('Getting {} tap from target {}'.format(tap_id, target_id))
        taps = self.get_taps(target_id)

        tap = False
        tap = next((item for item in taps if item["id"] == tap_id), False)

        if tap == False:
            raise Exception("Cannot find {} tap in {} target".format(tap_id, target_id))
        
        tap_dir = self.get_tap_dir(target_id, tap_id)
        if os.path.isdir(tap_dir):
            tap['files'] = self.parse_connector_files(tap_dir)
        else:
            raise Exception("Cannot find tap at {}".format(tap_dir))
        
        # Add target details
        tap['target'] = self.get_target(target_id)

        return tap

    def discover_tap(self, target_id, tap_id):
        self.logger.info('Discovering {} tap from target {}'.format(tap_id, target_id))
        command = "{} discover_tap --target {} --tap {}".format(self.etlwise_bin, target_id, tap_id)
        result = self.run_command(command, False)
        return result

    def get_streams(self, target_id, tap_id):
        self.logger.info('Getting {} tap streams from {} target'.format(tap_id, target_id))
        tap = self.get_tap(target_id, tap_id)

        try:
            streams = tap['files']['properties']['streams']
        except Exception as exc:
            raise Exception("Cannot find streams for {} tap in {} target. {}".format(tap_id, target_id, exc))
        
        return streams
    
    def get_stream(self, target_id, tap_id, stream_id):
        self.logger.info('Getting {} stream in {} tap in {} target'.format(stream_id, tap_id, target_id))
        streams = self.get_streams(target_id, tap_id)

        stream = False
        stream = next((item for item in streams if item["tap_stream_id"] == stream_id), False)

        if stream == False:
            raise Exception("Cannot find {} stream in {} tap in {} target".format(stream_id, tap_id, target_id))
        
        return stream
    
    def update_stream(self, target_id, tap_id, stream_id, params):
        self.logger.info('Updating {} stream in {} tap in {} target'.format(stream_id, tap_id, target_id))
        stream = self.get_stream(target_id, tap_id, stream_id)
        
        try:
            tap_dir = self.get_tap_dir(target_id, tap_id)
            properties_file = os.path.join(tap_dir, 'properties.json')
            properties = self.load_json(properties_file)
            tap_type = params["tapType"]
            print(tap_type)

            if tap_type == "tap-postgres":
                streams = properties["streams"]
                
                # Find the stream by stream_id
                for stream_idx, stream in enumerate(streams):
                    if stream["tap_stream_id"] == stream_id:
                        # Find the breadcrumb in metadata that needs to be updated 
                        for idx, mdata in enumerate(stream["metadata"]):
                            if stream["metadata"][idx]["breadcrumb"] == params["breadcrumb"]:
                                # Breadcrumb found, do the update
                                update_key = params["update"]["key"]
                                update_value = params["update"]["value"]
                                # Do only certain updates
                                if (update_key == "selected" and isinstance(update_value, bool)):
                                    stream["metadata"][idx]["metadata"]["selected"] = update_value
                                    # Set default replication method
                                    if stream["metadata"][idx]["breadcrumb"] == []:
                                        stream["metadata"][idx]["metadata"]["replication-method"] = "FULL_TABLE"

                                else:
                                    raise Exception("Unknown method to update")
        
                        # Save the new stream propertes
                        properties["streams"][stream_idx] = stream
                        self.save_json(properties, properties_file)

                return "Tap stream updated successfully"
            else:
                raise Exception("Not supported tap type {}".format(tap_type))
        except Exception as exc:
            raise Exception("Failed to update {} stream in {} tap in {} target. Invalid updated parameters: {} - {}".format(stream_id, tap_id, target_id, params, exc))

    def get_tap_logs(self, target_id, tap_id):
        self.logger.info('Getting {} tap logs from {} target'.format(tap_id, target_id))
        logs = []

        try:
            log_dir = self.get_tap_log_dir(target_id, tap_id)
            if os.path.isdir(log_dir):
                for log in os.listdir(log_dir):
                    if log.endswith('.log'):
                        logs.append(log)
        except Exception as exc:
            raise Exception("Cannot find logs for {} tap in {} target. {}".format(tap_id, target_id, exc))

        return logs  
    
    def get_tap_log(self, target_id, tap_id, log_id):
        self.logger.info('Getting {} tap log from {} tap in {} target'.format(log_id, target_id, tap_id))
        log_content = '_EMPTY_FILE_'
        try:
            log_file = os.path.join(self.get_tap_log_dir(target_id, tap_id), log_id)
            log = open(log_file, 'r')
            log_content = log.read()
            log.close()
        except Exception as exc:
            raise Exception("Error reading log file. {}".format(exc))
    
        return log_content
