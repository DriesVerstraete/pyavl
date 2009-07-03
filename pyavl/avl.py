'''
Created on Jun 8, 2009

@author: pankaj
'''

import pexpect
import os
from enthought.traits.api import HasTraits, List, Float, Dict, String, Int, Tuple,\
    Enum, cached_property, Python, Property, on_trait_change, Complex, Array, Instance, Directory, ReadOnly
from enthought.traits.ui.api import View, Item, Group, VGroup, ListEditor, TupleEditor, TextEditor, TableEditor
from enthought.traits.ui.table_column import ObjectColumn
import re
import numpy
from pyavl.case import Case
from pyavl.mass import Mass
#from pyavl.runcase import RunCase

    
class EigenMode(HasTraits):
    eigenvalue = Complex()
    # the = theta
    order = List(String, ['u', 'w', 'q', 'the', 'v', 'p', 'r', 'phi', 'x', 'y', 'z', 'psi'])
    eigenvector = Array(numpy.complex, shape=(12,))

class EigenMatrix(HasTraits):
    # include the control vector
    matrix = Array(numpy.float, shape=(12, (12, None)))
    order = List(String, ['u', 'w', 'q', 'the', 'v', 'p', 'r', 'phi', 'x', 'y', 'z', 'psi'])

class Parameter(HasTraits):
    name = String
    value = Float
    unit = String
    pattern = String
    cmd = String
    editor = TableEditor(
        auto_size    = False,
        columns  = [ ObjectColumn( name = 'name', editable=False, label='Parameter'),
                     ObjectColumn( name = 'value', label='Value' ), 
                     ObjectColumn( name = 'unit', editable=False, label='Unit')
                    ] )

class Constraint(HasTraits):
    name = String
    constrait_name = String
    value = Float
    pattern = String
    cmd = String
    editor = TableEditor(
        auto_size    = False,
        columns  = [ ObjectColumn( name = 'name', editable=False, label='Parameter'),
                     ObjectColumn( name = 'constraint_name', label='Constraint' ), 
                     ObjectColumn( name = 'value', editable=False, label='Value')
                    ] )


class RunCase(HasTraits):
    patterns = {'name':re.compile(r"""Operation of run case (?P<case_num>\d+)/(?P<num_cases>\d+):\s*(?P<case_name>.+?)\ *?\n"""),
                'constrained':re.compile(r"""(?P<cmd>[A-Z0-9]+)\s+(?P<pattern>.+?)\s+->\s+(?P<constraint>\S+)\s+=\s+(?P<val>[-+]?(\d+(\.\d*)?|\.\d+)([eE][-+]?\d+)?)"""),
                'constraint':re.compile(r"""(?P<sel>->)?\s*(?P<cmd>[A-Z0-9])+\s+(?P<pattern>.+?)\s+=\s+(?P<val>[-+]?(\d+(\.\d*)?|\.\d+)([eE][-+]?\d+)?)"""),
                'parameter':re.compile(r"""(?P<cmd>[A-Z]+)\s+(?P<pattern>.+?)\s+=\s+(?P<val>[-+]?(\d+(\.\d*)?|\.\d+)([eE][-+]?\d+)?)(\ +(?P<unit>\S+))?"""),
                'var':re.compile(r"""(?P<name>\S+?)\s*?=\s*?(?P<value>[-+]?(\d+(\.\d*)?|\.\d+)([eE][-+]?\d+)?)"""),
                'float':re.compile(r'(?P<value>[-+]?(\d+(\.\d*)?|\.\d+)([eE][-+]?\d+)?)'),
                'mode' :re.compile(r"""mode (\d+?):\s*?(?P<real>[-+]?(\d+(\.\d*)?|\.\d+)([eE][-+]?\d+)?)\s+(?P<imag>[-+]?(\d+(\.\d*)?|\.\d+)([eE][-+]?\d+)?)"""),
                'modeveccomp': re.compile(r"""(?P<name>[a-z]+?)(\s*?):\s*(?P<real>[-+]?(\d+(\.\d*)?|\.\d+)([eE][-+]?\d+)?)\s+(?P<imag>[-+]?(\d+(\.\d*)?|\.\d+)([eE][-+]?\d+)?)""")
                }
    number = Int
    name = String
    output = Dict(String, Float, {})
    
    traits_view = View(Group(Item('number',style='readonly'),
                             Item('name')),
                       Group(Item('parameter_view', editor=Parameter.editor, show_label=False), label='Parameters'),
                       Group(Item('constraint_view', editor=Constraint.editor, show_label=False), label='Constraints'),
                        Item() # so that groups are not tabbed
                       )
    
    # name, value
    parameters = Dict(String, Float, {})
    # pattern:name
    parameter_names = Dict(String, String, {})
    # name:(cmd,pattern,unit)
    parameters_info = Dict(String, Tuple(String, String, String), {})
    
    # TODO: fixit
    # name:pattern
    #constrained_params = Property(Dict(String, String), depends_on='constrained_patterns')
    @cached_property
    def _get_constrained_params(self):
        return self.constrained_patterns.keys()
    
    # name:pattern
    constrained_patterns = Dict(String, String, {'alpha':'lpha', 'beta':'eta',
                            'roll rate':'oll  rate', 'pitch rate':'itch rate',
                            'yaw rate':'aw   rate'})
    # auto-detect cmd from patterns
    #constrained_cmd = Dict(String, String, {'alpha':'A', 'beta':'B', 'roll rate':'R',
    #                        'pitch rate':'P', 'yaw rate':'Y'})
    # name:cmd
    constrained_cmd = Property(Dict, depends_on='constrained_patterns')
    @cached_property
    def _get_constrained_cmd(self):
        self.avl.sendline('oper')
        self.avl.expect(AVL.patterns['/oper'])
        self.avl.sendline(str(self.number))
        self.avl.expect(AVL.patterns['/oper'])
        lines = self.avl.before.readlines()
        lines = [line.strip() for line in lines]
        i1 = lines.index('------------      ------------------------')
        i2 = lines.index('------------      ------------------------', i1 + 1)
        constraint_lines = lines[i1 + 1:i2]
        groups = [re.match(RunCase.patterns['constrained'], line).groupdict() for line in constraint_lines]
        cmds = {}
        patterns = {}
        for group in groups:
            patterns[group['pattern']] = group['cmd']
        for param, pattern in self.constrained_params.iteritems():
            cmds[param] = patterns[pattern]
        AVL.goto_state(self.avl)
        return cmds
    
    # TODO: fixit
    # name:pattern
    #constraint_vars = Property(Dict(String, String), depends_on='constraint_patterns')
    @cached_property
    def _get_constraint_vars(self):
        return self.constraint_patterns.keys()
    constraint_patterns = Dict(String, String, {'alpha':'alpha', 'beta':'beta',
                            'roll rate':'pb/2V', 'yaw rate':'rb/2V', 'pitch rate':'qc/2V',
                            'lift coeff':'CL', 'side force coeff':'CY', 'roll coeff':'Cl roll mom',
                            'pitch coeff':'Cm pitchmom', 'yaw coeff':'Cn yaw  mom'})
    # constraint:cmd
    constraint_cmd = Property(Dict, depends_on='constraint_patterns')
    @cached_property
    def _get_constraint_cmd(self):
        self.avl.sendline('oper')
        self.avl.expect(AVL.patterns['/oper'])
        self.avl.sendline(str(self.number))
        self.avl.expect(AVL.patterns['/oper'])
        self.avl.sendline('a')
        self.avl.expect(AVL.patterns['/oper/a'])
        lines = self.avl.before.splitlines()
        self.avl.sendline()
        self.avl.expect(AVL.patterns['/oper'])
        lines = [line.strip() for line in lines]
        i1 = lines.index('- - - - - - - - - - - - - - - - -')
        i2 = lines.index('', i1 + 1)
        constraint_lines = lines[i1 + 1:i2]
        groups = [re.match(RunCase.patterns['constraint'], line).groupdict() for line in constraint_lines]
        cmds = {}
        patterns = {}
        for group in groups:
            patterns[group['pattern']] = group['cmd']
        for param, pattern in self.constrained_params.iteritems():
            cmds[param] = patterns[pattern]
        AVL.goto_state(self.avl)
        return cmds
    
    # constraints are corresponding to to the params in constraint_params
    # constrained : constraint_name, value
    constraints = Dict(String, Tuple(String, Float),
                                {'alpha': ('alpha', 0.0),
                                 'beta': ('beta', 0.0),
                                 'roll rate': ('roll rate', 0.0),
                                 'yaw rate': ('yaw rate', 0.0),
                                 'pitch rate': ('pitch rate', 0.0)}
                        )
    
    parameter_view = Property(List(Parameter), depends_on='parameters[]')
    constraint_view = Property(List(Constraint), depends_on='parameters[]')
    @cached_property
    def _get_parameter_view(self):
        l = []
        for k,v in self.parameters.iteritems():
            l.append(Parameter(name=k,value=float(v),unit=self.parameters_info[k][2]))
        print 'parameter_view:', l
        return l
    def _get_constraint_view(self):
        l = []
        return l
    
    @on_trait_change('constraints[]')
    def update_constraints(self):
        print 'constraints changed'
        self.avl.sendline('oper')
        self.avl.sendline()
        self.avl.expect(AVL.patterns['/'])
        for p, c in self.constraints.iteritems():
            p1 = self.constraint_cmd[p]
            c1 = self.constrained_cmd[c[0]]
            self.avl.sendline('oper')
            self.avl.expect(AVL.patterns['/oper'])
            self.avl.sendline('%s %s %f' % (p1, c1, c[1]))
            self.avl.expect(AVL.patterns['/oper'])
        AVL.goto_state(self.avl)
    
    @on_trait_change('parameters[]')
    def update_parameters(self):
        self.avl.sendline('oper')
        self.avl.sendline('m')
        self.avl.expect(AVL.patterns['/oper/m'])
        self.avl.sendline('V %f' % max(self.parameters['velocity'], 0.001))
        for p, v in self.parameters.iteritems():
            cmd = self.parameters_info[p][0]
            if cmd != 'V':
                self.avl.sendline('%s %f' % (cmd, v))
        AVL.goto_state(self.avl)
    
    @classmethod
    def get_constraint_params_from_avl(cls, avl, case_num=1):
        avl.sendline('oper')
        avl.expect(AVL.patterns['/oper'])
        avl.sendline(str(case_num))
        avl.expect(AVL.patterns['/oper'])
        avl.sendline('a')
        avl.expect(AVL.patterns['/oper/a'])
        if avl.match.groups('case_num') != str(case_num):
            #raise Exception('could not get case information for case num %d' % case_num)
            pass
        lines = avl.before.splitlines()
        lines = [line.strip() for line in lines]
        i1 = lines.index('- - - - - - - - - - - - - - - - -')
        i2 = lines.index('', i1 + 1)
        constraint_lines = lines[i1 + 1:i2]
        params = [re.search(RunCase.patterns['constraint'], line).group('pattern') for line in constraint_lines]
        avl.sendline()
        AVL.goto_state(avl)
        return params
    
    @classmethod
    def get_constrained_params_from_avl(cls, avl, case_num=1):
        avl.sendline('oper')
        avl.expect(AVL.patterns['/oper'])
        avl.sendline(str(case_num))
        avl.expect(AVL.patterns['/oper'])
        if avl.match.groups('case_num') != str(case_num):
            #raise Exception('could not get case information for case num %d' % case_num)
            pass
        lines = avl.before.splitlines()
        lines = [line.strip() for line in lines]
        i1 = lines.index('------------      ------------------------')
        i2 = lines.index('------------      ------------------------', i1 + 1)
        constraint_lines = lines[i1 + 1:i2]
        params = [re.match(RunCase.patterns['constrained'], line).group('pattern') for line in constraint_lines]
        AVL.goto_state(avl)
        return params
    
    @classmethod
    def get_case_from_avl(cls, avl, case_num):
        # TODO: parse constraints and parameters from avl
        avl.sendline('oper')
        avl.expect(AVL.patterns['/oper'])
        avl.sendline(str(case_num))
        avl.expect(AVL.patterns['/oper'])
        match = re.search((RunCase.patterns['name']), avl.before)
        name = match.group('case_name').strip()
        AVL.goto_state(avl)
        runcase = RunCase(name=name, number=case_num)
        runcase.avl = avl
        constrained_params = RunCase.get_constrained_params_from_avl(avl, case_num)
        for constrained_param in constrained_params:
            if constrained_param not in runcase.constrained_patterns.values():
                runcase.constrained_patterns[constrained_param] = constrained_param
        constraint_params = RunCase.get_constraint_params_from_avl(avl, case_num)
        for constraint_param in constraint_params:
            if constraint_param not in runcase.constraint_patterns.values():
                runcase.constraint_patterns[constraint_param] = constraint_param
        RunCase.get_parameters_info_from_avl(runcase, avl)
        AVL.goto_state(avl)
        return runcase
        
    def get_parameters_info_from_avl(self, avl):
        avl.sendline('oper')
        avl.expect(AVL.patterns['/oper'])
        avl.sendline('m')
        avl.expect(AVL.patterns['/oper/m'])
        avl.sendline()
        lines = avl.before.splitlines()
        lines = [line.strip() for line in lines if len(line.strip()) > 0]
        l2 = [line.startswith('Parameters') for line in lines]
        i1 = l2.index(True)
        i2 = - 1
        constraint_lines = lines[i1 + 1:i2]
        groups = [re.search(RunCase.patterns['parameter'], line).groupdict() for line in constraint_lines]
        params = {}
        AVL.goto_state(avl)
        #params.update(self.parameters)
        for group in groups:
            pattern = group['pattern']
            name = self.parameter_names.get(pattern, pattern)
            unit = group.get('unit', '')
            unit = unit if unit is not None else ''
            self.parameters_info[name] = (group['cmd'], pattern, unit)
            params[name] = float(group['val'])
        #self.parameters[name] = float(group['val'])
        self.parameters.update(params)
        AVL.goto_state(avl)
        
    def get_run_output(self):
        self.avl.sendline('oper')
        self.avl.expect(AVL.patterns['/oper'])
        self.avl.sendline('x')
        self.avl.expect(AVL.patterns['/oper'])
        ret = {}
        #print self.avl.before
        i1 = re.search(r"""Run case:\s*?.*?\n""", self.avl.before).end()
        i2 = re.search(r"""---------------------------------------------------------------""", self.avl.before[i1:]).start()
        text = self.avl.before[i1:i1 + i2]
        AVL.goto_state(avl)
        for match in re.finditer(RunCase.patterns['var'], text):
            ret[match.group('name')] = float(match.group('value'))
        self.output = ret
        AVL.goto_state(avl)
        return ret
    
    def get_modes(self):
        self.avl.sendline('mode')
        self.avl.expect(AVL.patterns['/mode'])
        self.avl.sendline('n')
        self.avl.expect(AVL.patterns['/mode'])
        if re.search(r'Eigenmodes not computed for run case', self.avl.before):
            print 'Error : \n', self.avl.before
            AVL.goto_state(avl)
            return
        ret = {}
        i1 = re.search(r"""Run case\s*?\d+?:.*?\n""", self.avl.before).end()
        i2 = re.search(r"""Run-case parameters for eigenmode analyses""", self.avl.before[i1:]).start()
        text = self.avl.before[i1 : i1 + i2]
        modes = []
        for mode_eval in re.finditer(RunCase.patterns['mode'], text):
            eigenvalue = float(mode_eval.group('real')) + 1j * float(mode_eval.group('imag'))
            mode = EigenMode(eigenvalue=eigenvalue)
            i = 0
            for match in re.finditer(RunCase.patterns['modeveccomp'], ' '.join(text[i + 1:i + 4])):
                i += 1
                mode.eigenvector[mode.order.index[match.groups('name')]] = float(mode_eval.groups('real')) + 1j * float(mode_eval.groups('imag'))
                if i > 11:
                    break
            modes.append(mode)
        AVL.goto_state(avl)
        return modes
    
    def get_system_matrix(self):
        self.avl.sendline('mode')
        self.avl.expect(AVL.patterns['/mode'])
        self.avl.sendline('n')
        self.avl.expect(AVL.patterns['/mode'])
        self.avl.sendline('s')
        self.avl.expect(AVL.patterns['/mode/s'])
        lines = [line for line in self.avl.before.splitlines()[3: - 1] if len(line) > 0]
        lines = [line.replace('**********', '      nan ') for line in lines]
        #print lines
        # fortran format to deceode
        # FORMAT(1X,12F10.4,3X,12G12.4)
        # 1 space, 12 floats of fixed width 10, 3 spaces 12 exponents of fixed width 12
        order = lines[0].replace('|', ' ').split()
        mat = numpy.empty((12, len(order)))
        for i, line in enumerate(lines[1:]):
            l1 = line[1:121]
            for j in xrange(12):
                mat[i, j] = float(l1[j * 10:(j + 1) * 10])
            l2 = line[124:]
            for j in xrange(len(l2) / 12):
                mat[i, 12 + j] = float(l2[j * 12:(j + 1) * 12])
        ret = EigenMatrix(order=order, matrix=mat)
        AVL.goto_state(self.avl)
        return ret
    
class AVL(HasTraits):
    '''
    A class representing an avl program instance.
    '''
    patterns = {'/'     : 'AVL   c>  ',
                '/oper' : re.compile(r"""\.OPER \(case (?P<case_num>\d)/(?P<num_cases>\d)\)   c>  """),
                '/plop' : r'Option, Value   \(or <Return>\)    c>  ',
                '/oper/a': re.compile(r"""Select new  constraint,value  for (?P<param>.*?)\s+c>  """),
                '/oper/m': r'Enter parameter, value  \(or  # - \+ N \)   c>  ',
                '/mode' : r'\.MODE   c>  ',
                '/mode/s': r'Enter output filename \(or <Return>\):',
                'num'   : r'(?P<val>[-+]?(\d+(\.\d*)?|\.\d+)([eE][-+]?\d+)?)'
                }
    run_cases = List(RunCase, [])
    state = String('/')
    selected_runcase = Int(1)
    case = Instance(Case)
    mass = Instance(Mass)
    cwd = Directory
    
    traits_view = View(Item('selected_runcase'))
    
    def _selected_case_changed(self):
        self.avl.sendline('oper')
        self.avl.sendline(str(self.selected_case))
        AVL.goto_state(self.avl)
    
    def __init__(self, path='', cwd='', logfile='/opt/idearesearch/avllog'):
        '''
        Constructor
        path is the directory where avl binary is found
        cwd is the working dir, where all the case related files are expected to be found (eg airfoil files)
        logfile is where all output is to be logged
        '''
        self.avl = pexpect.spawn(os.path.join(path, 'avl'), logfile=open(logfile, 'w'), cwd=cwd)
        self.avl.timeout = 10
        self.cwd = cwd
        self.disable_plotting()
        
    def execute_case(self, case_num=None):
        # TODO: implement
        if case_num is None:
            case_num = self.selected_case
        self.avl.sendline('oper')
        self.avl.expect(AVL.patterns['/oper'])
        self.avl.sendline(str(case_num))
        self.avl.expect(AVL.patterns['/oper'])
        self.avl.sendline('x')
        AVL.goto_state(self.avl)
        
        
    def disable_plotting(self):
        self.avl.sendline('plop')
        self.avl.sendline('g')
        AVL.goto_state(self.avl)
    
    @classmethod
    def goto_state(cls, avl, state='/'):
        for i in xrange(6):
            avl.sendline('')
            try:
                avl.expect(AVL.patterns['/'], timeout=1)
                return
            except pexpect.TIMEOUT:
                pass
        raise Exception('Can\'t reach base state')
    
    def get_output(self):
        #FIXME: implement
        pass
    
    def populate_runcases(self):
        self.avl.sendline('oper')
        self.avl.expect(AVL.patterns['/oper'])
        num_cases = int(self.avl.match.group('num_cases'))
        AVL.goto_state(self.avl)
        for case_num in xrange(1, num_cases + 1):
            self.run_cases.append(RunCase.get_case_from_avl(self.avl, case_num))
        self.selected_case = 1
    
    def load_case_from_file(self, filename):
        self.avl.sendline('load %s' % filename)
        if os.path.isabs(filename):
            f = open(filename)
        else:
            f = open(os.path.join([self.cwd, filename]))
        self.case = Case.case_from_input_file(f, cwd=self.cwd)
        f.close()
        AVL.goto_state(self.avl)
        self.populate_runcases()
    
    def load_mass_from_file(self, filename):
        self.mass = Mass.mass_from_file(filename)

def create_default_avl(*args,**kwargs):
    avl = AVL(cwd='/opt/idearesearch/avl/runs/')
    avl.load_case_from_file('/opt/idearesearch/avl/runs/vanilla.avl')
    return avl