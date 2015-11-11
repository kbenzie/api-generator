#!/usr/bin/env python


from __future__ import print_function
from os import path
import xml.etree.ElementTree as XML
import getopt
import json
import sys


def help():
    print('generate.py [-h] [-o <output dir>] [-n <client name>]')


def fail(message):
    print(message)
    sys.exit(1)


def is_identifier(identifier):
    nondigits = ['_', 'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k',
            'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x',
            'y', 'z', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K',
            'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X',
            'Y', 'Z']
    digits = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9']

    if not identifier[:1] in nondigits:
        return False

    characters = nondigits + digits

    for char in identifier[1:]:
        if not char in characters:
            return False

    return True


def include(node):
    include = '#' + node.tag + ' '
    form = node.attrib.get('form')
    if None == form or 'angle' == form:
        include += '<' + node.text + '>'
    elif 'quote' == form:
        include += '"' + node.text + '"'
    else:
        fail('invalid include form: ' + form)
    print(include)


def define(node):
    define = '#' + node.tag + ' ' + node.text

    params = node.findall('param')
    if 0 < len(params):
        param_names = []
        for param in params:
            param_names.append(param.text)
        define += '(' + ', '.join(param_names) + ')'

    value = node.find('value')
    if None != value:
        lines = value.text.split('\n')
        if 1 < len(lines):
            define += ' \\\n  ' + ' \\\n  '.join(lines)
        elif 1 == len(lines):
            define += ' ' + lines[0]
    print(define)


def typedef(node):
    typedef = 'typedef '


def generate(schema_file, output_dir, client_name):
    tree = XML.parse(schema_file)
    interface = tree.getroot()

    for node in interface:
        if 'include' == node.tag:
            include(node)
        elif 'define' == node.tag:
            define(node)
        elif 'typedef' == node.tag:
            typedef(node)


def main():
    options, arguments = getopt.getopt(sys.argv[1:], 'hs:o:n:')

    for arg in arguments:
        print('invalid argument:', arg)
        sys.exit(1)

    schema_file = "./demo.xml"
    output_dir = '.'
    client_name = 'Demo'

    for opt, arg in options:
        if opt in ('-h'):
            help()
            sys.exit(0)
        elif opt in ('-s'):
            if not path.exists(arg) or not path.isfile(arg):
                print('invalid schema file:', arg);
                sys.exit(1)
            schema = arg
        elif opt in ('-o'):
            if not path.exists(arg) or not path.isdir(arg):
                print('invalid directory:', arg)
                sys.exit(1)
            output_dir = arg
        elif opt in ('-n'):
            if not is_identifier(arg):
                print('invalid C89 identifier:', arg)
                sys.exit(1)
            client_name = arg

    generate(schema_file, output_dir, client_name)


if __name__ == '__main__':
    main()
