import ipaddress
import json
import os
import re
import socket
from cmd import Cmd
import logging

logging.basicConfig(level=logging.DEBUG, filename='debug_client_logs.txt',
                    format='%(asctime)s:%(lineno)d:%(threadName)s:%(message)s')


class MyClient(Cmd):
    """
    Class for creating a server instance
    """
    prompt = 'client> '
    intro = "Welcome to the Client Instance! Type ? to list commands"

    def __init__(self):
        """
        Constructor method for class MyClient
        arg - dictionary with keys 'client_name','ip_address', 'port_number'
        """
        super().__init__()
        self.disconnect_dict = {'message': 'request', 'type': 'DISCONNECT'}
        self.get_dict = {'message': 'request', 'type': 'GET', 'target': ''}
        self.del_dict = {'message': 'request', 'type': 'DELETE', 'target': ''}
        self.put_dict = {'message': 'request', 'type': 'PUT', 'target': '', 'content': '''garbage text'''}
        self.file_pattern = re.compile("(/[A-Z,a-z,0-9]{1,20}){0,10}/[A-Z,a-z,0-9]{1,10}\.[A-Z,a-z,0-9]{1,5}")
        self.folder_pattern = re.compile("(/[A-Z,a-z,0-9]{1,20}){1,10}/")
        self.state = False
        self.conn = ""
        self.cmdloop_with_keyboard_interrupt()

    def append_string_literals(self, base_string):
        return """{}\n""".format(base_string)

    def do_exit(self, inp):
        return True

    def help_exit(self):
        print('Exit the application. Shorthand: x q Ctrl-D.')

    def connect_validation(self, input_argument):
        try:
            argList = input_argument.split()
            if len(argList) == 2:
                if argList[0] == 'localhost':
                    ip_address = argList[0]
                else:
                    ip_address = ipaddress.ip_address(argList[0])

                if int(argList[1]) not in range(1, 65535):
                    logging.debug('Invalid Port Number')
                    print('Invalid Port Number')
                else:
                    port_number = int(argList[1])
                    return True
        except ValueError:
            logging.debug('Invalid Host')
            print('Invalid Host')
            return False

    def do_connect(self, inp):
        if not self.connect_validation(inp):
            self.state = False
        else:
            argList = inp.split()
            address = argList[0], int(argList[1])
            try:
                self.conn = socket.create_connection(address, timeout=5.0)
                print('Successfully Connected')
                self.state = True
            except socket.error as err:
                logging.debug(err)
                print('No server')
                self.state = False
            except ConnectionRefusedError as err:
                logging.debug(err)
                print('No server')
                self.state = False

    def help_connect(self):
        print("Provide IP Address and Port Number: (Example: connect localhost 9999)")

    def get_validation(self, input_argument):
        argList = input_argument.split()
        if len(argList) == 1 and self.file_pattern.fullmatch(argList[0]):
            return True
        else:
            return False

    def do_get(self, inp):
        if self.state and self.get_validation(inp):
            argList = inp.split()
            try:
                temp_dict = self.get_dict
                temp_dict['target'] = argList[0]
                temp_json = json.dumps(temp_dict)
                get_json = self.append_string_literals(temp_json)
                self.conn.sendall(get_json.encode('utf-8'))
                response_json = self.conn.recv(1024).decode('utf-8')
                response_dict = json.loads(response_json)
                print(response_dict['content'])
            except socket.timeout:
                logging.debug('Connection Timed Out')
                return self.exception_close()
            except ConnectionError as err:
                logging.debug(err)
                return self.exception_close()
        else:
            logging.debug('Wrong naming')

    def help_get(self):
        print("get <target> (Example: get /index.html)")

    def do_list(self, inp):
        logging.debug('Files in current working directory: ')
        for root, dirs, files in os.walk("."):
            del dirs[:]
            for name in files:
                print(name)

    def help_list(self):
        print("Lists files in current working directory: (Example: list )")

    def put_validation(self, input_argument):
        argList = input_argument.split()
        bool = False
        if len(argList) == 2 and self.file_pattern.fullmatch(argList[0]) and self.file_pattern.fullmatch(argList[1]):
            file_path = (os.path.join(os.getcwd(), argList[0][1:]))
            if os.path.isfile(file_path):
                bool = True
            else:
                print('Source file not found')
                bool = False
        else:
            bool = False
        return bool

    def exception_close(self):
        self.conn.close()
        print('Successfully Disconnected')
        return True

    def do_put(self, inp):
        try:
            if self.state and self.put_validation(inp):
                argList = inp.split()
                temp_dict = self.put_dict
                temp_dict['target'] = argList[1]
                with open(os.path.join(os.getcwd(), argList[0][1:]), 'rt') as f:
                    temp_dict['content'] = f.read()
                temp_json = json.dumps(temp_dict)
                put_json = self.append_string_literals(temp_json)
                self.conn.sendall(put_json.encode('utf-8'))
                response_json = self.conn.recv(1024).decode('utf-8')
                if response_json is not None:
                    response_dict = json.loads(response_json)
                    print('{0} {1}'.format(response_dict['code'], response_dict['content']))
        except socket.error as err:
            logging.debug('Server disconnected {}'.format(err))
            return self.exception_close()
        except ConnectionError as err:
            logging.debug('Server disconnected {}'.format(err))
            return self.exception_close()

    def help_put(self):
        print("put <source> <target> (Example: put test.html /finance/index.html)")

    def delete_validation(self, input_argument):
        argList = input_argument.split()
        if len(argList) == 1 and (self.file_pattern.fullmatch(argList[0]) or self.folder_pattern.fullmatch(argList[0])):
            return True
        else:
            return False

    def do_delete(self, inp):
        try:
            if self.state and self.delete_validation(inp):
                argList = inp.split()
                temp_dict = self.del_dict
                temp_dict['target'] = argList[0]
                temp_json = json.dumps(temp_dict)
                del_json = self.append_string_literals(temp_json)
                # print(put_json)
                self.conn.sendall(del_json.encode('utf-8'))
                response_json = self.conn.recv(1024).decode('utf-8')
                response_dict = json.loads(response_json)
                print('{0} {1}'.format(response_dict['code'], response_dict['content']))
        except socket.error as err:
            logging.debug('Server disconnected {}'.format(err))
            return self.exception_close()
        except ConnectionError as err:
            logging.debug('Server disconnected {}'.format(err))
            return self.exception_close()

    def help_delete(self):
        print("delete <target> (Example: delete /finance/test.html)")

    def sess_disconnect(self):
        try:
            if self.state:
                temp_dict = self.disconnect_dict
                dis_json = self.append_string_literals(json.dumps(temp_dict))
                logging.debug(dis_json)
                self.conn.sendall(dis_json.encode('utf-8'))
                return self.exception_close()
            else:
                return True
        except socket.error:
            logging.debug('Connection Timed Out')
        except ConnectionRefusedError:
            logging.debug('Connection Closed')

    def do_disconnect(self, inp):
        return self.sess_disconnect()

    def emptyline(self):
        pass

    def help_disconnect(self):
        print("Disconnect Server (Example: disconnect)")

    def cmdloop_with_keyboard_interrupt(self):
        doQuit = False
        while not doQuit:
            try:
                self.cmdloop()
                doQuit = True
            except KeyboardInterrupt:
                return self.sess_disconnect()


    def default(self, inp):
        if inp == 'x' or inp == 'q':
            return self.sess_disconnect()
        else:
            print("{} not a valid command!! Type ? to list commands".format(inp))


if __name__ == "__main__":
    client = MyClient()
