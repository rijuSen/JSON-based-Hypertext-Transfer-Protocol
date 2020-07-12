import argparse
import socket
import threading
import time
import json
import os
import re
import errno
import logging
from cmd import Cmd

logging.basicConfig(level=logging.DEBUG, filename='debug_logs.txt',
                    format='%(asctime)s:%(lineno)d:%(threadName)s:%(message)s')


def append_string_literals(base_string):
    return """{}\n""".format(base_string)


class MyServer(Cmd):
    """
    Class for creating a server instance
    """
    prompt = 'server> '

    def __init__(self, port_number):
        """
        Constructor method for class MyServer
        arg - dictionary with keys 'server_name','ip_address', 'port_number', 'number_of_connections'
        """
        super().__init__()
        self.address = 'localhost', port_number
        self.connections = []
        self.threads = []
        self.threads.append(threading.current_thread())
        self.file_pattern = re.compile("(/[A-Z,a-z,0-9]{1,20}){0,10}/[A-Z,a-z,0-9]{1,10}\.[A-Z,a-z,0-9]{1,5}")
        self.folder_pattern = re.compile("(/[A-Z,a-z,0-9]{1,20}){1,10}/")
        self.bad_req_dict = {"message": "response", "code": "401", "content": "Bad Request"}
        self.base_dir = 'www'
        self.create_base_dir()
        self.get_response_dict = {"message": "response", "code": "200", "content": "sample"}
        self.put_new_response_dict = {"message": "response", "code": "201", "content": "Ok"}
        self.put_mod_response_dict = {"message": "response", "code": "202", "content": "Modified"}
        self.del_success_response_dict = {"message": "response", "code": "203", "content": "Ok"}
        self.not_found_response_dict = {"message": "response", "code": "400", "content": "Not Found"}
        self.unknown_error_response_dict = {"message": "response", "code": "402", "content": "Unknown Error"}
        t = threading.Thread(target=self.start_server)
        t.setDaemon(True)
        t.start()
        self.cmdloop_with_keyboard_interrupt()

    def create_base_dir(self):
        try:
            os.mkdir(self.base_dir)
        except FileExistsError:
            pass
        except os.error as err:
            logging.debug('error raised{err}')

    def file_create(self, file_path):
        complete_path = os.path.join(self.base_dir, file_path)
        if not os.path.exists(os.path.dirname(complete_path)):
            try:
                os.makedirs(os.path.dirname(complete_path))
            except OSError as exc:  # Guard against race condition
                if exc.errno != errno.EEXIST:
                    raise

    def get_function(self, request_dict):
        target = request_dict['target']
        if self.file_pattern.fullmatch(target):
            file_path = os.path.join(os.getcwd(), self.base_dir, *target.split('/'))
            if os.path.exists(file_path):
                with open(file_path, 'rt') as f:
                    content = f.read()
                temp_dict = self.get_response_dict
                temp_dict['content'] = content
            else:
                temp_dict = self.not_found_response_dict
        else:
            temp_dict = self.bad_req_dict
        return temp_dict

    def put_function(self, request_dict):
        target = request_dict['target']
        if self.file_pattern.fullmatch(target):
            folder_name = self.folder_pattern.search(target)
            folder_name = folder_name.group(0)
            file_path = os.path.join(os.getcwd(), self.base_dir, *target.split('/'))
            folder_path = os.path.join(os.getcwd(), self.base_dir, *folder_name.split('/'))
            if not os.path.exists(file_path):
                os.makedirs(folder_path, exist_ok=True)
                with open(file_path, 'wt') as f:
                    logging.debug('file created')
                    f.write(request_dict['content'])
                temp_dict = self.put_new_response_dict
            else:
                with open(file_path, 'wt') as f:
                    logging.debug('file modeified')
                    f.write(request_dict['content'])
                temp_dict = self.put_mod_response_dict
        else:
            temp_dict = self.bad_req_dict
        return temp_dict

    def delete_function(self, request_dict):
        target = request_dict['target']
        try:
            if self.file_pattern.fullmatch(target):
                file_path = os.path.join(os.getcwd(), self.base_dir, *target.split('/'))
                if os.path.exists(file_path):
                    os.remove(file_path)
                    temp_dict = self.del_success_response_dict
                else:
                    temp_dict = self.not_found_response_dict
            elif self.folder_pattern.fullmatch(target):
                logging.debug(target)
                folder_path = os.path.join(os.getcwd(), self.base_dir, *target.split('/'))
                logging.debug(folder_path)
                if os.path.exists(folder_path):
                    os.removedirs(folder_path)
                    logging.debug(folder_path)
                    temp_dict = self.del_success_response_dict
                else:
                    temp_dict = self.not_found_response_dict
            else:
                temp_dict = self.bad_req_dict
        except os.error as err:
            logging.debug(err)
            temp_dict = self.unknown_error_response_dict
        return temp_dict

    def connection_instance(self, connection_instance):
        conn, addr = connection_instance[0], connection_instance[1]
        logging.debug('Client address {}'.format(addr))
        try:
            while True:
                req_json = conn.recv(1024).decode('utf-8')
                logging.debug(req_json)
                if req_json is not None:
                    logging.debug(req_json)
                    req_dict = json.loads(req_json)
                    logging.debug(req_json)
                    if 'message' in req_dict.keys() and 'type' in req_dict.keys() and req_dict['message'] == 'request':
                        if req_dict['type'] == 'GET' and 'target' in req_dict.keys():
                            response_dict = self.get_function(req_dict)
                        elif req_dict['type'] == 'PUT' and 'target' in req_dict.keys() and 'content' in req_dict.keys():
                            response_dict = self.put_function(req_dict)
                        elif req_dict['type'] == 'DELETE' and 'target' in req_dict.keys():
                            response_dict = self.delete_function(req_dict)
                        elif req_dict['type'] == 'DISCONNECT':
                            conn.close()
                            break
                    else:
                        response_dict = self.bad_req_dict
                    response_json = append_string_literals(json.dumps(response_dict))
                    logging.debug(response_json)
                    conn.sendall(response_json.encode('utf-8'))
            logging.debug('Thread about to be terminated')
        except socket.error as error:
            logging.debug('Error occurred {}'.format(error))
        except json.JSONDecodeError as err:
            logging.debug('Wrong json format')

    def start_server(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.bind(self.address)
            s.listen()
            logging.debug('Waiting for connections')
            while True:
                time.sleep(0.2)
                con_tuple = s.accept()
                # threading to accept multiple requests together
                thread = threading.Thread(target=self.connection_instance, args=[con_tuple])
                thread.setDaemon(True)
                self.connections.append(con_tuple)
                self.threads.append(thread)
                thread.start()
                thread.join()
        except (KeyboardInterrupt, SystemExit):
            self.close_connections()
            logging.debug('keyboard interrupt')
        except socket.error as err:
            logging.debug('Some error {}'.format(err))

    def cmdloop_with_keyboard_interrupt(self):
        doQuit = False
        while not doQuit:
            try:
                self.cmdloop()
                doQuit = True
            except (KeyboardInterrupt, SystemExit):
                self.close_connections()
                print("Closing Server Application!!")
                return True

    def close_connections(self):
        for conn, addr in self.connections:
            conn.close()

    def do_show(self, inp):
        for conn, addr in self.connections:
            print('Server connected with {} on port {}'.format(addr[0], addr[1]))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Server Application')
    # parser.add_argument("-p", help="input the port number on which the Server will listen on",
    #                     type=int)
    requiredNamed = parser.add_argument_group('required named arguments')
    requiredNamed.add_argument("-p", help='input the port number on which the Server will listen on', required=True, type=int)
    args = parser.parse_args()
    port_number = vars(args)['p']
    if port_number in range(1, 65536):
        MyServer(port_number)
    else:
        logging.debug("Invalid Port Number")

