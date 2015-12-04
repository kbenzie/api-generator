#!/usr/bin/env python

# Copyright (c) 2015 Kenneth Benzie
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.  IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

from __future__ import print_function
from os import path
import xml.etree.ElementTree as XML
import getopt
import json
import sys


indent = '  '
prefix = ''
stub = None
variables = []


class Variable:
    name = ''
    values = []

    def __init__(self, name, values):
        self.name = name
        self.values = values


class DoxygenParam:
    __name = None
    __text = None
    __form = None

    def __init__(self, name, node):
        if None == name:
            raise Exception('Parameter name must not be None')
        self.__name = name
        if None != node:
            param = node.find('param')
            if None != param:
                self.__text = param.text
                form = param.attrib.get('form')
                if '' != form:
                    self.__form = form

    def output(self):
        param = ''
        if None != self.__text:
            param += '@param'
            if '' != self.__form:
                param += '[' + self.__form + '] '
            else:
                param += ' '
            param += self.__name + ' ' + self.__text
        return param


class Doxygen:
    brief = None
    detail = None
    params = []
    ret = None
    see = None

    def __init__(self, node):
        self.init(node)

    def init(self, node):
        self.params = []
        if None != node:
            brief = node.find('brief')
            if None != brief:
                self.brief = brief.text
            else:
                self.brief = None
            detail = node.find('detail')
            if None != detail:
                self.detail = detail.text
            else:
                self.detail = None
            ret = node.find('return')
            if None != ret:
                self.ret = ret.text
            else:
                self.ret = None
            see = node.find('see')
            if None != see:
                self.see = see.text
            else:
                self.see = None
        else:
            self.brief = None
            self.detail = None
            self.ret = None
            self.see = None

    def empty(self):
        if None == self.brief and None == self.detail and 0 == \
                len(self.params) and None == self.ret and None == self.see:
            return True
        return False

    def output(self):
        sections = []
        if None != self.brief:
            sections.append('/// ' + '@brief ' + replace_prefix(self.brief) + '\n')
        if None != self.detail:
            detail = ''
            for line in self.detail.split('\n'):
                detail += '/// ' + line + '\n'
            sections.append(replace_prefix(detail))
        if 0 != len(self.params):
            param_section = ''
            for param in self.params:
                param_section += '/// ' + param + '\n'
            if '' != param_section:
                sections.append(replace_prefix(param_section))
        if None != self.ret:
            sections.append('/// @return ' + replace_prefix(self.ret) + '\n')
        if None != self.see:
            sections.append('/// @see ' + replace_prefix(self.see) + '\n')
        text = ''
        if 0 != len(sections):
            text = '///\n'.join(sections)
        return text.strip()


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
    return identifier.replace("${prefix}", prefix).replace("${Prefix}", prefix.capitalize()).replace("${PREFIX}", prefix.upper())


def replace_variables(text):
    start = text.find('${')
    while -1 != start:
        end = text.find('}')
        var_name = text[start + 2:end]
        replaced = False
        for variable in variables:
            if var_name in variable.name:
                text = text.replace('${' + var_name + '}', variable.values[0])
                replaced = True
        if not replaced:
            raise Exception('could not replace:', var_name)
        start = text.find('${')
    return text


def replace_stub(text, name, arguments):
    stub = ''
    text = text.replace("${name}", name.replace("${prefix}", ""))
    capturing = False

    loop_variable = None
    loop_iterator = ''
    loop_lines = []

    for line in text.split('\n'):
        if '${foreach}' in line:
            capturing = True

            # Reset loop state
            loop_variable = None
            loop_iterator = ''
            loop_lines = []

            expr = line[line.find('(') + 1:line.find(')')]
            in_pos = expr.find('in')
            iter_name = expr[:in_pos].strip()
            var_name = expr[in_pos + 2:].strip()
            for variable in variables:
                if var_name == variable.name:
                    for value in variable.values:
                        loop_variable = variable
                        loop_iterator = iter_name

            if None == loop_variable:
                raise Exception('invalid ${foreach} variable', var_name)
        elif '${endforeach}' in line:
            # TODO: Write loop
            for value in loop_variable.values:
                for line in loop_lines:
                    stub += line.replace('${' + loop_iterator + '}', value) + '\n'
            capturing = False
        elif capturing:
            loop_lines.append(line)
        else:
            stub += line + '\n'

    stub = stub.replace("${forward}", ', '.join(arguments))
    # TODO: Support any numbered argument!
    stub = stub.replace("${0}", arguments[0])
    stub = stub.replace("${prefix}", prefix)
    return replace_variables(stub)


def include(node, newline):
    if None == node.text:
        raise Exception('missing include file')
    name = replace_prefix(node.text.strip())
    include = '#' + node.tag + ' '
    form = node.attrib.get('form')
    if None == form or 'angle' == form:
        include += '<' + name + '>'
    elif 'quote' == form:
        include += '"' + name + '"'
    else:
        raise Exception('invalid include form: ' + form)
    if newline:
        include += '\n'
    print(include)


def define(node, newline):
    docs = Doxygen(node.find('doxygen'))
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
    if not docs.empty():
        print(docs.output())
    print(define)


def struct(node, semicolon, newline):
    doxygen = Doxygen(node.find('doxygen'))
    struct = 'struct'
    if node.text:
        name = replace_prefix(node.text.strip())
        if not is_identifier(name):
            raise Exception('invalid struct name: ' + name)
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
                    doxygen_member = Doxygen(member.find('doxygen')).output()
                    type = member.find('type')
                    if None != type:
                        member_decl = ''
                        if '' != doxygen_member:
                            doxygen_members = doxygen_member.split('\n')
                            doxygen_member = ''
                            for line in doxygen_members:
                                doxygen_member += indent + line + '\n'
                            doxygen_member = doxygen_member.rstrip()
                            member_decl += doxygen_member + '\n'
                        member_decl += indent + replace_prefix(type.text.strip())
                        if member.text:
                            member_decl += ' ' + \
                                    replace_prefix(member.text.strip())
                        member_decls.append(member_decl)
                    member_function = member.find('function')
                    if None != member_function:
                        function_form = member_function.attrib.get('form')
                        if 'pointer' != function_form:
                            raise Exception('struct member function is not a function pointer')
                        member_decl = ''
                        if '' != doxygen_member:
                            member_decl += indent + doxygen_member + '\n'
                        member_decl += indent + function(member_function, False, False, False)
                        member_decls.append(member_decl)
                    member_union = member.find('union')
                    if None != member_union:
                        union_decls = []
                        if '' != doxygen_member:
                            union_decls.append(doxygen_member)
                        union_decls.extend(union(member_union, False, False, False).split('\n'))
                        union_decl = '\n'.join([indent + decl for decl in union_decls])
                        member_decls.append(union_decl)
            if 0 < len(member_decls):
                struct += '\n' + ';\n'.join(member_decls) + ';\n'
            struct += '}'
    if semicolon:
        struct += ';'
    if newline:
        struct += '\n\n'
    docs = doxygen.output()
    if '' != docs:
        print(docs)
    sys.stdout.write(struct)


def union(node, semicolon, newline, out = True):
    union = 'union'
    if node.text:
        name = replace_prefix(node.text.strip())
        if not is_identifier(name):
            raise Exception('invalid union name: ' + name)
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
                            raise Exception('union member has no name')
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
    doxygen = Doxygen(node.find('doxygen')).output()
    if '' != doxygen:
        enum = doxygen + '\n' + enum
    if node.text:
        name = node.text.strip()
        if '' != name:
            enum += ' ' + replace_prefix(name)
    enum += ' {'
    scope = node.find('scope')
    # TODO Output nice diagnostics for unexpected input, use is_identifier()
    if None == scope:
        raise Exception("missing enum scope tag")
    constants = scope.findall('constant')
    if 0 < len(constants):
        enum += '\n'
        constant_decls = []
        for constant in constants:
            if None != constant:
                decl = ''
                doxygen = Doxygen(constant.find('doxygen')).output()
                if '' != doxygen:
                    for line in doxygen.split('\n'):
                        decl = indent + line + '\n'
                if None == constant.text:
                    raise Exception("invalid enum constant")
                decl += indent + replace_prefix(constant.text.strip())
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
    docs = Doxygen(node.find('doxygen'))
    name = replace_prefix(node.text.strip())
    if None == name:
        raise Exception('missing typedef type name')
    type = node.find('type')
    if None == type:
        raise Exception('missing typedef type')
    if '' != docs:
        print(docs.output())
    sys.stdout.write('typedef ')
    if None != type.getchildren():
        generate(type, False, False)
        if None != type.text:
            sys.stdout.write(replace_prefix(type.text.strip()))
        sys.stdout.write(' ' + name);
    print(';\n')


def function(node, semicolon, newline, out = True):
    doxygen = Doxygen(node.find('doxygen'))
    if None == node.text:
        raise Exception('missing function name')
    return_type = node.find('return')
    if None == return_type:
        raise Exception('missing function return')
    if None == return_type.text:
        raise Exception("missing function return type name")
    doxygen_return = return_type.find('doxygen')
    if None != doxygen_return:
        tag = doxygen_return.find('return')
        if None != tag:
            doxygen.ret = tag.text
    function = replace_prefix(return_type.text.strip()) + ' '
    prefix_name = node.text.strip()
    name = replace_prefix(prefix_name)
    form = node.attrib.get('form')
    if None != form:
        if 'pointer' == form:
            function += '(*' + name + ')('
        else:
            raise Exception('invalid function form: ' + form)
    else:
        function += name + '('
    params = node.findall('param')
    doxygen.params = []
    param_names = []
    if 0 < len(params):
        param_decls = []
        for param in params:
            param_type = param.find('type')
            if None == param_type:
                raise Exception('missing function parameter type')
            if None == param_type.text:
                raise Exception('missing function parameter type name')
            decl = replace_prefix(param_type.text.strip())
            if None != param.text:
                decl += ' ' + replace_prefix(param.text.strip())
                doxygen_param = DoxygenParam(param.text, param.find('doxygen')).output()
                if '' != doxygen_param:
                    doxygen.params.append(doxygen_param)
                param_names.append(param.text)
            param_decls.append(decl)
        function += ', '.join(param_decls)
    function += ')'
    if semicolon:
        function += ';'
    if newline:
        function += '\n'
    if not doxygen.empty() and None == stub:
        function = doxygen.output() + '\n' + function
    if out:
        print(function)
        if None != stub:
            print('{\n' + replace_stub(stub.text, prefix_name, param_names) + '\n}\n')
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
            raise Exception('invalid scope form: ' + form)
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
        raise Exception('missing guard name')
    name = replace_prefix(node.text.strip())
    form = node.attrib.get('form')
    if 'include' == form:
        print('#ifndef ' + replace_prefix(name))
        print('#define ' + replace_prefix(name) + '\n')
        generate(node, semicolon, True)
        print('#endif  // ' + replace_prefix(name))
    elif 'defined':
        print('#ifdef ' + name)
        generate(node, semicolon, False)
        print('#endif  // ' + replace_prefix(name))
    else:
        print('#ifndef ' + name)
        generate(node, semicolon, False)
        print('#endif  // ' + name)
    if newline:
        print()


def code(node):
    if node.text:
        print(replace_prefix(node.text))


def generate(parent, semicolon = True, newline = True):
    if None == stub:
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
    else:
        print(replace_prefix('#include <${prefix}/${prefix}.h>\n'))
        for node in parent:
            if 'guard' == node.tag:
                for guard_node in node:
                    if 'function' == guard_node.tag:
                        function(guard_node, False, False)
            if 'function' == node.tag:
                function(node, False, False)


def help():
    print('generate.py [options] <schema>\n')
    print('options:')
    print('        -h                            show this help message')
    print('        -p <prefix>                   identifier to be prefixed')
    print('        -s <name>                     output function stubs')
    print('        -v <variable>:<value>[;...]   add user variable')


def main():
    global indent
    global prefix
    global stub

    if 1 == len(sys.argv):
        help()
        sys.exit(1)

    # TODO Add options for outputting header or source files
    options, arguments = getopt.getopt(sys.argv[1:], 'hp:s:v:')

    if 0 == len(arguments):
        raise Exception('missing schema file')

    if 1 != len(arguments):
        for arg in arguments:
            raise Exception('invalid argument:', arg)
    schema = arguments[0]
    if not path.exists(schema) or not path.isfile(schema):
        raise Exception('invalid schema file:', schema);

    tree = XML.parse(schema)
    interface = tree.getroot()

    for opt, arg in options:
        if opt in ('-h'):
            help()
            sys.exit(0)
        elif opt in ('-p'):
            if not is_identifier(arg):
                raise Exception('invalid C prefix:', arg)
            prefix = arg
        elif opt in ('-s'):
            stubs = interface.find('stubs')
            for node in stubs:
                if arg == node.attrib.get('name'):
                    stub = node
            if None == stub:
                raise Exception('could not find stub named:', arg)
        elif opt in ('-v'):
            name_end = str(arg).find(':')
            variable = Variable(arg[0:name_end], arg[name_end + 1:].split(';'))
            variables.append(variable)

    generate(interface)


if __name__ == '__main__':
    main()
