import ply.lex as lex
import ply.yacc as yacc
import os

import conf
import control
import midimesg

#This prevents ply's deprecated use of md5 instead of hashlib
import warnings
warnings.filterwarnings('ignore')

class Parser():
    """
    Base class for a lexer/parser that has the rules defined as methods
    """
    tokens = ()
    precedence = ()

    def __init__(self, **kw):
        self.debug = kw.get('debug', 0)
        self.names = { }
        try:
            modname = os.path.split(os.path.splitext(__file__)[0])[1] + "_" \
            + self.__class__.__name__
        except:
            modname = "parser"+"_"+self.__class__.__name__
        self.debugfile = modname + ".dbg"
        self.tabmodule = modname + "_" + "parsetab"

        # Build the lexer and parser
        lex.lex(module=self, debug=self.debug)
        yacc.yacc(module=self,
                  debug=self.debug,
                  debugfile=self.debugfile,
                  write_tables=0) #FIXME: Smarter parsetab managing it's needed
                  #tabmodule="parsetab.py")

    def run(self):
        while 1:
            try:
                s = raw_input('parser > ')
            except EOFError:
                break
            if not s: continue
            yacc.parse(s)

    def load(self, path):
        self.names = {}
        f = open(path, 'r')
        yacc.parse(f.read())
        f.close()
        
class WidParser(Parser):
    literals = '.,=()+'
    tokens = (
        'NUMBER',
        'WIIMOTE', 'WIIBUTTON', 'NUNCHUK', 'NUNBUTTON', 'BTNEVENT',
        'AXISEVENT',
        'NOTE', 'PROG_CHG'
        )

    t_WIIMOTE = r'Wiimote'
    t_WIIBUTTON = r'A|B|Left|Right|Up|Down|Minus|Plus|Home|1|2'
    t_NUNCHUK = r'Nunchuk'
    t_NUNBUTTON = r'C|Z'
    t_BTNEVENT = r'Press|Release'
    t_AXISEVENT = r'Roll|Pitch|Acc'
    t_NOTE = r'NOTE'
    t_PROG_CHG = r'PROG_CHG'
    t_ignore  = ' \t'
        
    def __init__(self):
        Parser.__init__(self)
        self.conf = conf.Conf()
        
    def t_COMMENT(self, t):
        r'\#.*'
        pass
        
    def t_NUMBER(self, t):
        r'\d+'
        t.value = int(t.value)    
        return t
        
    def t_newline(self, t):
        r'\n+'
        t.lexer.lineno += len(t.value)

    def t_error(self, t):
        print "Illegal character '%s'" % t.value[0]
        t.lexer.skip(1)

    def p_program(self, p):
        """ program : program expression
                    | expression """

        p[0] = None

    def p_expression(self, p):
        """ expression : buttonassign """
                      #| axisassign"""

        p[0] = p[1]

    """
    def p_axisassign(self, p):
        \""" axisassign : axis '=' midiwheel \"""
        
    def p_axis(self, p):
        \""" axis : WIIMOTE '.' AXISEVENT
                 | NUNCHUK '.' AXISEVENT \"""

        if p[1] == 'Wiimote':
            button = control.WiimoteAxis(''.join(p[1:]))
        elif p[1] == 'Nunchuk':
            button = control.NunchukAxis(''.join(p[1:]))
                 
        p[0] = button
    """    
    
    def p_buttonassign(self, p):
        """ buttonassign : buttoncomb '=' midicmd
                         | buttoncomb '.' BTNEVENT '=' midicmd """

        if len(p) == 4:
            p[1].set_press_action(p[3])
            if p[3].reversible:
                p[1].set_release_action(-p[3])
        else:
            if p[3] == 'Press':
                p[1].set_press_action(p[5])
            else:
                p[1].set_release_action(p[5])

        self.conf.add_btn(p[1])
        p[0] = p[1]

    def p_buttoncomb(self, p):
        """ buttoncomb : '(' buttoncomb '+' button ')'
                       | button """

        if len(p) == 2:
            button = self.conf.get_btn(p[1])
            if button:
                p[0] = button
            else:
                p[0] = p[1]
        else:
            p[0] = p[2] + p[4]

    def p_button(self, p):
        """ button : WIIMOTE '.' WIIBUTTON
                   | NUNCHUK '.' NUNBUTTON """

        if p[1] == 'Wiimote':
            button = control.WiimoteButton(''.join(p[1:]))
        elif p[1] == 'Nunchuk':
            button = control.NunchukButton(''.join(p[1:]))
                 
        p[0] = button

    def p_midicmd(self, p):
        """ midicmd : midimesg
                    | midimesg '+' 
                    | midimesg '-' 
                    | midimesg '+' NUMBER
                    | midimesg '-' NUMBER """
                    
        if len(p) == 2:
            p[0] = p[1]
        else:
            step = 1
            if len(p) == 4: step = p[3]
            if p[2] == '-': step = -step
            p[0] = midimesg.Data1Step(p[1], step)

    def p_midimeg(self, p):
        """ midimesg : PROG_CHG
                    | PROG_CHG '(' NUMBER ')'
                    | NOTE '(' NUMBER ',' NUMBER ')' 
                    | NOTE '(' NUMBER ',' NUMBER ',' NUMBER ')' """
                    
        if len(p) == 2:
            p[0] = midimesg.ProgChg(1)
        elif len(p) == 5:
            p[0] = midimesg.ProgChg(p[3])
        elif len(p) == 7:
            p[0] = midimesg.Note(p[3], p[5])
        else:
            p[0] = midimesg.Note(p[3], p[5], p[7])

    def p_error(self, p):
        if p:
            print "Syntax error at '%s'" % p.value
        else:
            print "Syntax error at EOF"
