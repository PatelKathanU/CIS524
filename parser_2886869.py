#!/usr/bin/env python3

import sys

#  Token and Lexer
# A small enum for token kinds
(
    T_ID,       # identifier
    T_INT,      # integer constant
    T_REAL,     # real constant
    T_IF,
    T_THEN,
    T_ELSE,
    T_LET,
    T_IN,
    T_END,
    T_INT_TYPE,     # 'int'
    T_REAL_TYPE,    # 'real'
    T_SEMI,     # ';'
    T_COLON,    # ':'
    T_EQ,       # '='
    T_LPAREN,   # '('
    T_RPAREN,   # ')'
    T_PLUS,     # '+'
    T_MINUS,    # '-'
    T_STAR,     # '*'
    T_SLASH,    # '/'
    T_LT,       # '<'
    T_LE,       # '<='
    T_GT,       # '>'
    T_GE,       # '>='
    T_EQEQ,     # '=='
    T_NE,       # '<>'
    T_EOF,
    T_DUMMY,
) = range(28)

KEYWORDS = {
    'if':    T_IF,
    'then':  T_THEN,
    'else':  T_ELSE,
    'let':   T_LET,
    'in':    T_IN,
    'end':   T_END,
    'int':   T_INT_TYPE,
    'real':  T_REAL_TYPE,
}

class Token:
    def __init__(self, kind, text):
        self.kind = kind
        self.text = text

    def __repr__(self):
        return f"Token({self.kind}, '{self.text}')"

class Lexer:
    def __init__(self, text):
        self.text = text
        self.pos = 0
        self.length = len(text)

    def peek_char(self):
        if self.pos < self.length:
            return self.text[self.pos]
        return '\0'

    def get_char(self):
        if self.pos < self.length:
            ch = self.text[self.pos]
            self.pos += 1
            return ch
        return '\0'

    def skip_whitespace(self):
        while True:
            ch = self.peek_char()
            if ch.isspace():
                self.get_char()
            else:
                break

    def is_identifier_start(self, ch):
        return ch.isalpha() or ch == '_'

    def is_identifier_part(self, ch):
        return ch.isalnum() or ch == '_'

    def get_next_token(self):
        self.skip_whitespace()
        ch = self.peek_char()
        if ch == '\0':
            return Token(T_EOF, "EOF")
        if ch == ';':
            self.get_char()
            return Token(T_SEMI, ';')
        if ch == ':':
            self.get_char()
            return Token(T_COLON, ':')
        if ch == '=':
            self.get_char()
            if self.peek_char() == '=':
                self.get_char()
                return Token(T_EQEQ, '==')
            return Token(T_EQ, '=')
        if ch == '(':
            self.get_char()
            return Token(T_LPAREN, '(')
        if ch == ')':
            self.get_char()
            return Token(T_RPAREN, ')')
        if ch == '+':
            self.get_char()
            return Token(T_PLUS, '+')
        if ch == '-':
            self.get_char()
            return Token(T_MINUS, '-')
        if ch == '*':
            self.get_char()
            return Token(T_STAR, '*')
        if ch == '/':
            self.get_char()
            return Token(T_SLASH, '/')
        if ch == '<':
            self.get_char()
            if self.peek_char() == '=':
                self.get_char()
                return Token(T_LE, '<=')
            elif self.peek_char() == '>':
                self.get_char()
                return Token(T_NE, '<>')
            return Token(T_LT, '<')
        if ch == '>':
            self.get_char()
            if self.peek_char() == '=':
                self.get_char()
                return Token(T_GE, '>=')
  
        if self.is_identifier_start(ch):
            start_pos = self.pos
            while self.is_identifier_part(self.peek_char()):
                self.get_char()
            text = self.text[start_pos:self.pos]
            tk = KEYWORDS.get(text.lower(), T_ID)
            return Token(tk, text)
            
        if ch.isdigit():
            start_pos = self.pos
            has_dot = False
            while self.peek_char().isdigit() or self.peek_char() == '.':
                nxt = self.peek_char()
                if nxt == '.':
                    if has_dot:
                        break
                    else:
                        has_dot = True
                self.get_char()
            num_str = self.text[start_pos:self.pos]
            # Distinguish int vs real
            if '.' in num_str:
                return Token(T_REAL, num_str)
            else:
                return Token(T_INT, num_str)

        # If we get here, we have an unrecognized character => error
        self.get_char()
        # We can handle it as an error or skip it:
        return Token(T_EOF, "EOF")


#  Parser / Interpreter

class Parser:
    def __init__(self, lexer):
        self.lexer = lexer
        self.token = None
        self.error_flag = False

        self.next_token()

    def next_token(self):
        self.token = self.lexer.get_next_token()

    def match(self, kind):
        # If token kind matches, consume it otherwise, set error_flag
        if self.token.kind == kind:
            self.next_token()
        else:
            self.error_flag = True

    def current_kind(self):
        return self.token.kind

    def parse_program(self):
        """
        <prog> ::= <let-in-end> { <let-in-end> }
        Keep going until we see EOF or no more blocks.
        """
        results = []
        while self.current_kind() != T_EOF:
            result = self.parse_let_in_end()
            if self.error_flag:
                # If error occurred in this block, print Error, then reset error to parse the next block
                print("Error")
                self._skip_until_next_let_end()
                self.error_flag = False
            else:
                print(result)

    def _skip_until_next_let_end(self):
        """
        If we got an error in a block, skip tokens until we either
        find another 'let' or reach EOF, so we can try to parse the
        next block fresh.
        """
        while self.current_kind() not in (T_LET, T_EOF):
            self.next_token()

    def parse_let_in_end(self):
        """
        <let-in-end> ::= let <decl-list> in <type> ( <expr> ) end ;
        Returns the numeric result of that expression or sets error_flag.
        """
        # Expect 'let'
        self.match(T_LET)
        # local environment: var -> (type_str, value)
        env = {}
        self.parse_decl_list(env)

        # Expect 'in'
        if not self.error_flag:
            self.match(T_IN)

        # parse type
        cast_type = None
        if not self.error_flag:
            if self.current_kind() == T_INT_TYPE:
                cast_type = 'int'
                self.match(T_INT_TYPE)
            elif self.current_kind() == T_REAL_TYPE:
                cast_type = 'real'
                self.match(T_REAL_TYPE)
            else:
                self.error_flag = True

        # Expect '('
        if not self.error_flag:
            self.match(T_LPAREN)
        
        # parse <expr>
        val = 0.0
        if not self.error_flag:
            val = self.parse_expr(env)

        # Expect ')'
        if not self.error_flag:
            self.match(T_RPAREN)
        
        # Expect 'end'
        if not self.error_flag:
            self.match(T_END)
        
        # Expect ';'
        if not self.error_flag:
            self.match(T_SEMI)

        # If error found, return None
        if self.error_flag:
            return None
        # Otherwise cast the result
        if cast_type == 'int':
            return int(val)
        else:
            return float(val)

    def parse_decl_list(self, env):
        """
        <decl-list> ::= <decl> { <decl> }
        """
        self.parse_decl(env)
        while not self.error_flag and self.current_kind() == T_ID:
            self.parse_decl(env)

    def parse_decl(self, env):
        """
        <decl> ::= id : <type> = <expr> ;
        """
        if self.current_kind() != T_ID:
            self.error_flag = True
            return
        varname = self.token.text
        self.match(T_ID)
        self.match(T_COLON)

        # parse <type>
        if self.current_kind() == T_INT_TYPE:
            var_type = 'int'
            self.match(T_INT_TYPE)
        elif self.current_kind() == T_REAL_TYPE:
            var_type = 'real'
            self.match(T_REAL_TYPE)
        else:
            self.error_flag = True
            return

        self.match(T_EQ)

        # parse <expr>
        val = self.parse_expr(env)

        self.match(T_SEMI)

        if self.error_flag:
            return

        # Store in env, cast to the type
        if var_type == 'int':
            env[varname] = ('int', int(val))
        else:
            env[varname] = ('real', float(val))

    #  Expression parsing

    def parse_expr(self, env):
        """
        <expr> ::= <term> { + <term> | - <term> }
                 | if <cond> then <expr> else <expr>
        """
        if self.current_kind() == T_IF:
            # if <cond> then <expr> else <expr>
            return self.parse_if_expr(env)
        else:
            return self.parse_add_sub(env)

    def parse_if_expr(self, env):
        """
        if <cond> then <expr> else <expr>
        """
        self.match(T_IF)
        cond_val = self.parse_cond(env)
        self.match(T_THEN)
        true_expr_val = self.parse_expr(env)
        self.match(T_ELSE)
        false_expr_val = self.parse_expr(env)
        return true_expr_val if cond_val else false_expr_val

    def parse_cond(self, env):
        """
        <cond> ::= <oprnd> < <oprnd>
                 | <oprnd> <= <oprnd>
                 | <oprnd> > <oprnd>
                 | <oprnd> >= <oprnd>
                 | <oprnd> == <oprnd>
                 | <oprnd> <> <oprnd>
        We parse the left operand, then a comparison operator, then the right operand.
        """
        left = self.parse_oprnd(env)
        op = self.current_kind()

        # The valid comparison tokens:
        if op not in (T_LT, T_LE, T_GT, T_GE, T_EQEQ, T_NE):
            self.error_flag = True
            return False

        self.next_token()
        right = self.parse_oprnd(env)

        if op == T_LT:
            return left < right
        elif op == T_LE:
            return left <= right
        elif op == T_GT:
            return left > right
        elif op == T_GE:
            return left >= right
        elif op == T_EQEQ:
            return abs(left - right) < 1e-15
        elif op == T_NE:
            return abs(left - right) > 1e-15
        return False

    def parse_oprnd(self, env):
        """
        <oprnd> ::= id | intnum
        But from examples, we might have real constants too.
        We only use the integer portion in <cond> if it's T_INT, but let's handle T_REAL safely too.
        """
        if self.current_kind() == T_ID:
            name = self.token.text
            self.next_token()
            if name not in env:
                self.error_flag = True
                return 0.0
            return env[name][1]
        elif self.current_kind() == T_INT:
            val = int(self.token.text)
            self.next_token()
            return val
        elif self.current_kind() == T_REAL:
            val = float(self.token.text)
            self.next_token()
            return val
        else:
            self.error_flag = True
            return 0.0

    def parse_add_sub(self, env):
        """
        <term> { + <term> | - <term> }
        """
        value = self.parse_term(env)
        while self.current_kind() in (T_PLUS, T_MINUS):
            op = self.current_kind()
            self.next_token()
            rhs = self.parse_term(env)
            if op == T_PLUS:
                value = value + rhs
            else:
                value = value - rhs
        return value

    def parse_term(self, env):
        """
        <factor> { * <factor> | / <factor> }
        """
        value = self.parse_factor(env)
        while self.current_kind() in (T_STAR, T_SLASH):
            op = self.current_kind()
            self.next_token()
            rhs = self.parse_factor(env)
            if op == T_STAR:
                value = value * rhs
            else:
                if abs(rhs) < 1e-15:
                    self.error_flag = True
                    return 0.0
                value = value / rhs
        return value

    def parse_factor(self, env):
        """
        <factor> ::= ( <expr> ) | id | number | <type> ( id )
        """
        k = self.current_kind()
        if k == T_LPAREN:
            self.match(T_LPAREN)
            val = self.parse_expr(env)
            self.match(T_RPAREN)
            return val
        elif k == T_ID:
            name = self.token.text
            self.match(T_ID)
            if name not in env:
                self.error_flag = True
                return 0.0
            return env[name][1]
        elif k == T_INT:
            val = int(self.token.text)
            self.match(T_INT)
            return val
        elif k == T_REAL:
            val = float(self.token.text)
            self.match(T_REAL)
            return val
        elif k in (T_INT_TYPE, T_REAL_TYPE):
            type_str = 'int' if (k == T_INT_TYPE) else 'real'
            self.next_token() 
            self.match(T_LPAREN)
            if self.current_kind() != T_ID:
                self.error_flag = True
                return 0.0
            var_name = self.token.text
            self.next_token()
            self.match(T_RPAREN)

            if var_name not in env:
                self.error_flag = True
                return 0.0
            original_value = env[var_name][1]
            if type_str == 'int':
                return int(original_value)
            else:
                return float(original_value)
        else:
            self.error_flag = True
            return 0.0


def main():
    if len(sys.argv) < 2:
        print("Usage: python parser_xxxxxxx.py <filename>")
        return

    filename = sys.argv[1]
    try:
        with open(filename, 'r') as f:
            text = f.read()
    except:
        print("Error opening file:", filename)
        return

    lexer = Lexer(text)
    parser = Parser(lexer)
    parser.parse_program()

if __name__ == "__main__":
    main()
