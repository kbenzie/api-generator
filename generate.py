#!/usr/bin/env python


from __future__ import print_function
from os import path
import xml.etree.ElementTree as XML
import getopt
import json
import sys


indent = '  '
prefix = 'demo_'


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


def include(node, newline):
    if None == node.text:
        fail('massing include file')
    name = node.text.strip()
    include = '#' + node.tag + ' '
    form = node.attrib.get('form')
    if None == form or 'angle' == form:
        include += '<' + name + '>'
    elif 'quote' == form:
        include += '"' + name + '"'
    else:
        fail('invalid include form: ' + form)
    if newline:
        include += '\n'
    print(include)


def define(node, newline):
    define = '#' + node.tag + ' ' + prefix.upper() + node.text
    params = node.findall('param')
    # TODO Output nice diagnostics for unexpected input, use is_identifier()
    if 0 < len(params):
        param_names = []
        for param in params:
            param_names.append(param.text)
        define += '(' + ', '.join(param_names) + ')'
    value = node.find('value')
    if None != value:
        lines = value.text.split('\n')
        if 1 < len(lines):
            continuation = ' \\\n'
            define += continuation + indent + (continuation + indent).join(lines)
        elif 1 == len(lines):
            define += ' ' + lines[0]
    if newline:
        define += '\n'
    print(define)


def struct(node, semicolon, newline):
    struct = 'struct'
    if node.text:
        name = node.text.strip()
        if not is_identifier(name):
            fail('invalid struct name: ' + name)
        struct += ' ' + prefix + name
    scope = node.find('scope')
    # TODO Output nice diagnostics for unexpected input, use is_identifier()
    if None != scope:
        members = scope.findall('member')
        if 0 < len(members):
            struct += ' {'
            member_decls = []
            for member in members:
                if None != member:
                    type = member.find('type')
                    if None != type:
                        member_decl = indent + type.text.strip()
                        if member.text:
                            member_decl += ' ' + member.text.strip()
                        member_decls.append(member_decl)
            if 0 < len(member_decls):
                struct += '\n' + ';\n'.join(member_decls) + ';\n'
            struct += '}'
    if semicolon:
        struct += ';'
    if newline:
        struct += '\n\n'
    sys.stdout.write(struct)


def enum(node, semicolon, newline):
    enum = 'enum'
    if node.text:
        name = node.text.strip()
        if '' != name:
            enum += ' ' + prefix + name
    enum += ' {'
    scope = node.find('scope')
    # TODO Output nice diagnostics for unexpected input, use is_identifier()
    if None == scope:
        fail("missing enum scope tag")
    constants = scope.findall('constant')
    if 0 < len(constants):
        enum += '\n'
        constant_decls = []
        for constant in constants:
            if None != constant:
                if None == constant.text:
                    fail("invalid enum constant")
                decl = indent + constant.text.strip()
                value = constant.find('value')
                if None != value:
                    decl += ' = ' + value.text.strip()
                constant_decls.append(decl)
        enum += ',\n'.join(constant_decls) + '\n'
    enum += '}'
    if semicolon:
        enum += ';'
    if newline:
        enum += '\n\n'
    sys.stdout.write(enum)


def typedef(node, newline):
    name = node.text.strip()
    if None == name:
        fail('missing typedef type name')
    name = prefix + name
    type = node.find('type')
    if None == type:
        fail('missing typedef type')
    sys.stdout.write('typedef ')
    if None != type.getchildren():
        generate(type, False, False)
        sys.stdout.write(' ' + type.text.strip())
        sys.stdout.write(' ' + name);
    print(';\n')



def function(node, semicolon, newline):
    if None == node.text:
        fail('missing function name')
    return_type = node.find('return')
    if None == return_type:
        fail('missing function return')
    if None == return_type.text:
        fail("missing function return type name")
    function = return_type.text + ' ' + prefix + node.text.strip() + '('
    params = node.findall('param')
    if 0 < len(params):
        param_decls = []
        for param in params:
            param_type = param.find('type')
            if None == param_type:
                fail('missing function parameter type')
            if None == param_type.text:
                fail('missing function parameter type name')
            decl = param_type.text
            if param.text:
                decl += ' ' + param.text
            param_decls.append(decl)
        function += ', '.join(param_decls)
    function += ')'
    body = node.find('scope')
    if None != body:
        # TODO don't print body when in header mode
        function += ' '
        sys.stdout.write(function)
        scope(body, False, False)
    elif semicolon:
        function += ';'
        print(function)
    if newline:
        print()


def comment(node, newline):
    comment = '// '
    if node.text:
        lines = node.text.split('\n')
        comment += '\n// '.join(lines)
    if newline:
        comment += '\n'
    print(comment)


def block(node):
    generate(node, False, False)
    print()


def scope(node, semicolon, newline):
    scope = ''
    open = True
    close = True
    form = node.attrib.get('form')
    if form:
        if 'open' == form:
            close = False
        elif 'close' == form:
            open = False
        else:
            fail('invalid scope form: ' + form)
    name = ''
    if node.text:
        name = node.text.strip()
    if open:
        if '' == name:
            print('{')
        else:
            print(name + ' {')
    generate(node, semicolon, newline)
    if close:
        if '' == name:
            print('}')
        else:
            print('}  // ' + name)
    if newline:
        print()


def guard(node, semicolon, newline):
    if not node.text:
        fail('missing guard name')
    name = node.text.strip()
    form = node.attrib.get('form')
    if 'include' == form:
        print('#ifndef ' + prefix.upper() + name)
        print('#define ' + prefix.upper() + name + '\n')
        generate(node, semicolon, True)
        print('#endif  // ' + prefix.upper() + name)
    else:
        print('#ifndef ' + name)
        generate(node, semicolon, False)
        print('#endif  // ' + name)
    if newline:
        print()


def generate(parent, semicolon = True, newline = True):
    for node in parent:
        if 'include' == node.tag:
            include(node, newline)
        elif 'define' == node.tag:
            define(node, newline)
        elif 'struct' == node.tag:
            struct(node, semicolon, newline)
        elif 'enum' == node.tag:
            enum(node, semicolon, newline)
        elif 'typedef' == node.tag:
            typedef(node, newline)
        elif 'function' == node.tag:
            function(node, semicolon, newline)
        elif 'comment' == node.tag:
            comment(node, newline)
        elif 'block' == node.tag:
            block(node)
        elif 'scope' == node.tag:
            scope(node, semicolon, newline)
        elif 'guard' == node.tag:
            guard(node, semicolon, newline)


def help():
    print('generate.py [options] <schema>')
    print('\noptions:')
    print('        -h                      show this help message')
    print('        -p <prefix>             identifier to be prefixed')


def main():
    global indent
    global prefix

    if 1 == len(sys.argv):
        help()
        sys.exit(1)

    # TODO Add options for outputting header or source files
    options, arguments = getopt.getopt(sys.argv[1:], 'hs:o:p:')

    if 0 == len(arguments):
        fail('missing schema file')

    if 1 != len(arguments):
        for arg in arguments:
            print('invalid argument:', arg)
            sys.exit(1)
    schema = arguments[0]
    if not path.exists(schema) or not path.isfile(schema):
        fail('invalid schema file:' + schema);

    schema_file = "./demo.xml"

    for opt, arg in options:
        if opt in ('-h'):
            help()
            sys.exit(0)
        elif opt in ('-p'):
            if not is_identifier(arg):
                print('invalid C prefix:', arg)
                sys.exit(1)
            prefix = arg

    tree = XML.parse(schema_file)
    interface = tree.getroot()
    generate(interface)


if __name__ == '__main__':
    main()
