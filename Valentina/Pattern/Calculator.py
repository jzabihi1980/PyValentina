####################################################################################################
#
# PyValentina - A Python implementation of Valentina Pattern Drafting Software
# Copyright (C) 2017 Fabrice Salvaire
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
####################################################################################################

####################################################################################################

import ast
import logging

import astunparse
# import astor

from Valentina.Graph.DirectedAcyclicGraph import DirectedAcyclicGraph

####################################################################################################

_module_logger = logging.getLogger(__name__)

####################################################################################################

class NodeVisitor(ast.NodeVisitor):

    ##############################################

    def __init__(self, calculator):

        super(NodeVisitor, self).__init__()
        self._calculator = calculator
        self._dependencies = []

    ##############################################

    @property
    def dependencies(self):
        return self._dependencies

    ##############################################

    # def visit(self, node):

    #     print(node)
    #     super(NodeVisitor, self).visit(node)

    ##############################################

    def visit_Call(self, node):

        function = node.func
        if isinstance(function, ast.Attribute) and function.value.id == '__calculator__':
            dag = self._calculator.dag
            if function.attr == '_function_Line':
                for arg in node.args:
                    self._dependencies.append(self._calculator._name_to_point(arg.s))
        self.generic_visit(node)

####################################################################################################

class Calculator:

    _logger = _module_logger.getChild('Calculator')

    ##############################################

    def __init__(self, measurements):

        self._measurements = measurements

        self._dag = DirectedAcyclicGraph()
        self._cache  = {'__calculator__': self}
        self._points = {}
        self._current_operation = None

    ##############################################

    @property
    def measurements(self):
        return self._measurements

    @property
    def dag(self):
        return self._dag

    @property
    def cache(self):
        return self._cache

    ##############################################

    def _update_cache(self, named_expression):

        self._cache[named_expression.name] = named_expression.value

    ##############################################

    def add_point(self, point):

        self._points[point.name] = point

    ##############################################

    def set_current_segment(self, vector):

        self._current_segment = vector

    ##############################################

    def unset_current_segment(self):

        self._current_segment = None
        # self._logger.info('Unset current segment')

    ##############################################

    def _name_to_point(self, name):

        return self._points[name]

    ##############################################

    def _name_to_vector_point(self, name):

        return self._points[name].vector

    ##############################################

    def _names_to_vector_points(self, *names):

        return [self._name_to_vector_point(name) for name in names]

    ##############################################

    # Fixme: special functions
    #   increments ?
    #   Length of curve: Spl_A_B
    #   Angle of line: AngleLine_A_B
    #   radius of arcs
    #   Angles of curves: Angle1Spl_A_B Angle2Spl_A_B
    #   Length of control points: C1LengthSpl_A_B C2LengthSpl_A_B
    #   functions

    def _function_Angle1Spl(self, point_name1, point_name2):
        point1, point2 = self._names_to_vector_points(point_name1, point_name2)
        return 0

    def _function_Angle2Spl(self, point_name1, point_name2):
        point1, point2 = self._names_to_vector_points(point_name1, point_name2)
        return 0

    def _function_AngleLine(self, point_name1, point_name2):
        point1, point2 = self._names_to_vector_points(point_name1, point_name2)
        return (point2 - point1).orientation()

    def _function_CurrentLength(self):
        return self._current_segment.magnitude()

    def _function_C1LengthSpl(self, point_name1, point_name2):
        point1, point2 = self._names_to_vector_points(point_name1, point_name2)
        return 0

    def _function_C2LengthSpl(self, point_name1, point_name2):
        point1, point2 = self._names_to_vector_points(point_name1, point_name2)
        return 0

    def _function_Line(self, point_name1, point_name2):
        point1, point2 = self._names_to_vector_points(point_name1, point_name2)
        return (point2 - point1).magnitude()

    def _function_Spl(self, point_name1, point_name2):
        point1, point2 = self._names_to_vector_points(point_name1, point_name2)
        return 0

####################################################################################################

class Expression:

    _logger = _module_logger.getChild('Expression')

    ##############################################

    def __init__(self, expression, calculator=None):

        self._expression = str(expression)
        self._calculator = calculator

        self._ast = None
        self._dependencies = None
        self._code = None
        self._value = None
        self._value_error = False

    ##############################################

    @property
    def expression(self):
        return self._expression

    @property
    def dependencies(self):
        return self._dependencies

    ##############################################

    def __str__(self):
        return self._expression

    ##############################################

    def is_float(self):

        try:
            float(self._expression)
            return True
        except ValueError:
            return False

    ##############################################

    def _find_name(self, prefix, start=0):

        expression = self._expression
        start = expression.find(prefix, start)
        if start is -1:
            return None, None
        index = start + 1
        while index < len(expression):
            c = expression[index]
            if 'a' <= c <= 'z' or 'A' <= c <= 'Z' or '0' <= c <= '9' or c in '_':
                index += 1
            else:
                break
        return expression[start:index], index + 1

    ##############################################

    def _compile(self):

        expression = self._expression
        self._logger.info("expression '{}'".format(expression))

        # Python don't accept identifier starting with @
        # https://docs.python.org/3.5/reference/lexical_analysis.html#identifiers
        if '@' in expression:
            custom_measurements = []
            start = 0
            while True:
                name, start = self._find_name('@', start)
                if name is None:
                    break
                else:
                    custom_measurements.append(name)
            for measurement in custom_measurements:
                expression = self.expression.replace(measurement, self._calculator.measurements[measurement].name)

        functions = []
        for function in (
                'Angle1Spl_',
                'Angle2Spl_',
                'AngleLine_',
                'CurrentLength',
                'C1LengthSpl_',
                'C2LengthSpl_',
                'Line_',
                'Spl_',
        ):
            start = 0
            while True:
                name, start = self._find_name(function, start)
                if name is None:
                    break
                else:
                    functions.append(name)
        # self._logger.info('Functions ' + str(functions))
        for function_call in functions:
            parts = function_call.split('_')
            function = parts[0]
            args = parts[1:]
            pythonised_function = '__calculator__._function_' + function + '(' + ', '.join(["'{}'".format(x) for x in args]) + ')'
            # self._logger.info('Function {} {} -> {}'.format(function, args, pythonised_function))
            expression = expression.replace(function_call, pythonised_function)

        self._logger.info("Pythonised expression '{}'".format(expression))

        # Fixme: What is the (supported) grammar ?
        # http://beltoforion.de/article.php?a=muparser
        # http://beltoforion.de/article.php?a=muparserx
        self._ast = ast.parse(expression, mode='eval')
        node_visitor = NodeVisitor(self._calculator)
        node_visitor.generic_visit(self._ast)
        self._dependencies = node_visitor.dependencies
        self._code = compile(self._ast, '<string>', mode='eval')
        # print('AST', astunparse.dump(self._ast))
        # print('AST -> Python', astunparse.unparse(self._ast))
        ## print('AST -> Python', astor.to_source(self._ast.body))

    ##############################################

    def eval(self):

        if self._code is None:
            self._compile()

        try:
            self._value = eval(self._code, self._calculator.cache)
            self._value_error = False
        except NameError:
            self._value = None
            self._value_error = True
        # except AttributeError as e:
        #     self._logger.warning(e)
        #     self._value = None

        self._logger.info('Eval {} = {}'.format(self._expression, self._value))

    ##############################################

    def set_dirty(self):

        self._value = None
        self._value_error = False

    ##############################################

    @property
    def value(self):

        if self._value is None and self._value_error is False:
            self.eval()
        return self._value

####################################################################################################

class NamedExpression(Expression):

    ##############################################

    def __init__(self, name, expression, calculator=None):

        Expression.__init__(self, expression, calculator)
        self._name = name

    ##############################################

    @property
    def name(self):
        return self._name
