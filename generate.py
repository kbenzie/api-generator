#!/usr/bin/env python


from __future__ import print_function
from os import path
import xml.etree.ElementTree as XML
import getopt
import json
import sys


indent = '  '
prefix = ''


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


def replace_prefix(identifier):
    return identifier.replace("${prefix}", prefix)


def include(node, newline):
    if None == node.text:
        fail('massing include file')
    name = replace_prefix(node.text.strip())
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
    define = '#' + node.tag + ' ' + replace_prefix(node.text.strip()).upper()
    params = node.findall('param')
    # TODO Output nice diagnostics for unexpected input, use is_identifier()
    if 0 < len(params):
        param_names = []
        for param in params:
            param_names.append(replace_prefix(param.text.strip()))
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
        name = replace_prefix(node.text.strip())
        if not is_identifier(name):
            fail('invalid struct name: ' + name)
        struct += ' ' + name
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
                        member_decl = indent + replace_prefix(type.text.strip())
                        if member.text:
                            member_decl += ' ' + \
                                    replace_prefix(member.text.strip())
                        member_decls.append(member_decl)
                    member_function = member.find('function')
                    if None != member_function:
                        function_form = member_function.attrib.get('form')
                        if 'pointer' != function_form:
                            fail('struct member function is not a function pointer')
                        member_decls.append(indent + function(member_function,
                            False, False, False))
                    member_union = member.find('union')
                    if None != member_union:
                        union_decls = union(member_union, False, False,
                                False).split('\n')
                        union_decl = '\n'.join([indent + decl \
                                for decl in union_decls])
                        member_decls.append(union_decl)
            if 0 < len(member_decls):
                struct += '\n' + ';\n'.join(member_decls) + ';\n'
            struct += '}'
    if semicolon:
        struct += ';'
    if newline:
        struct += '\n\n'
    sys.stdout.write(struct)


def union(node, semicolon, newline, out = True):
    union = 'union'
    if node.text:
        name = replace_prefix(node.text.strip())
        if not is_identifier(name):
            fail('invalid union name: ' + name)
        union += ' ' + name
    scope = node.find('scope')
    if None != scope:
        members = scope.findall('member')
        if 0 < len(members):
            union += ' {'
            member_decls = []
            for member in members:
                if None != member:
                    member_name = replace_prefix(member.text.strip())
                    type = member.find('type')
                    if None != type:
                        member_decl = indent + replace_prefix(type.text.strip())
                        if None == member.text:
                            fail('union member has no name')
                        member_decl += ' ' + member_name
                        member_decls.append(member_decl)
                    struct = member.find('struct')
                    if None != struct:
                        struct_name = replace_prefix(struct.text.strip())
                        if None != struct_name:
                            member_decl = indent + 'struct ' + struct_name + \
                                    ' ' + member_name
                            member_decls.append(member_decl)
            if 0 < len(member_decls):
                union += '\n' + ';\n'.join(member_decls) + ';\n'
            union += '}'
    if semicolon:
        union += ';'
    if newline:
        union += '\n\n'
    if out:
        sys.stdout.write(union)
    else:
        return union


def enum(node, semicolon, newline):
    enum = 'enum'
    if node.text:
        name = node.text.strip()
        if '' != name:
            enum += ' ' + replace_prefix(name)
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
                decl = indent + replace_prefix(constant.text.strip())
                value = constant.find('value')
                if None != value:
                    decl += ' = ' + replace_prefix(value.text.strip())
                constant_decls.append(decl)
        enum += ',\n'.join(constant_decls) + '\n'
    enum += '}'
    if semicolon:
        enum += ';'
    if newline:
        enum += '\n\n'
    sys.stdout.write(enum)


def typedef(node, newline):
    name = replace_prefix(node.text.strip())
    if None == name:
        fail('missing typedef type name')
    type = node.find('type')
    if None == type:
        fail('missing typedef type')
    sys.stdout.write('typedef ')
    if None != type.getchildren():
        generate(type, False, False)
        if None != type.text:
            sys.stdout.write(' ' + replace_prefix(type.text.strip()))
        sys.stdout.write(' ' + name);
    print(';\n')


def function(node, semicolon, newline, out = True):
    if None == node.text:
        fail('missing function name')
    return_type = node.find('return')
    if None == return_type:
        fail('missing function return')
    if None == return_type.text:
        fail("missing function return type name")
    function = replace_prefix(return_type.text.strip()) + ' '
    name = replace_prefix(node.text.strip())
    form = node.attrib.get('form')
    if None != form:
        if 'pointer' == form:
            function += '(*' + name + ')('
        else:
            fail('invalid function form: ' + form)
    else:
        function += name + '('
    params = node.findall('param')
    if 0 < len(params):
        param_decls = []
        for param in params:
            param_type = param.find('type')
            if None == param_type:
                fail('missing function parameter type')
            if None == param_type.text:
                fail('missing function parameter type name')
            decl = replace_prefix(param_type.text.strip())
            if param.text:
                decl += ' ' + replace_prefix(param.text.strip())
            param_decls.append(decl)
        function += ', '.join(param_decls)
    function += ')'
    if semicolon:
        function += ';'
    if newline:
        function += '\n'
    if out:
        print(function)
    else:
        return function


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
        name = replace_prefix(node.text.strip())
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
    name = replace_prefix(node.text.strip())
    form = node.attrib.get('form')
    if 'include' == form:
        print('#ifndef ' + replace_prefix(name).upper())
        print('#define ' + replace_prefix(name).upper() + '\n')
        generate(node, semicolon, True)
        print('#endif  // ' + replace_prefix(name).upper())
    elif 'defined':
        print('#ifdef ' + name)
        generate(node, semicolon, False)
        print('#endif  // ' + replace_prefix(name).upper())
    else:
        print('#ifndef ' + name)
        generate(node, semicolon, False)
        print('#endif  // ' + name)
    if newline:
        print()


def code(node):
    if node.text:
        print(node.text)


def generate(parent, semicolon = True, newline = True):
    for node in parent:
        if 'include' == node.tag:
            include(node, newline)
        elif 'define' == node.tag:
            define(node, newline)
        elif 'struct' == node.tag:
            struct(node, semicolon, newline)
        elif 'union' == node.tag:
            union(node, semicolon, newline)
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
        elif 'code' == node.tag:
            code(node)


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

    for opt, arg in options:
        if opt in ('-h'):
            help()
            sys.exit(0)
        elif opt in ('-p'):
            if not is_identifier(arg):
                print('invalid C prefix:', arg)
                sys.exit(1)
            prefix = arg

    tree = XML.parse(schema)
    interface = tree.getroot()
    generate(interface)


if __name__ == '__main__':
    main()
