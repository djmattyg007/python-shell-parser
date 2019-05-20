from shell_statement_parser.parser import Parser

try:
    import readline
except:
    pass


statement = input("> ")
print(repr(statement))

parser = Parser()
commands, first_cmd = parser.parse(statement)
print(commands)
print("")

for i, command in enumerate(commands):
    print("cmd", i)
    for word in command:
        print(" ", word)
print("")


def output_statement(cmd):
    statement = str(cmd)
    cur_pipe_cmd = cmd.pipe_command
    while cur_pipe_cmd:
        statement += " | " + str(cur_pipe_cmd)
        cur_pipe_cmd = cur_pipe_cmd.pipe_command
    return statement

def output_statements(first_cmd):
    statements = []
    cmd = first_cmd
    while cmd:
        if cmd.next_command_operator:
            cur_cmd = cmd
            statement = ""
            while cur_cmd.next_command_operator:
                statement += output_statement(cur_cmd)
                statement += " " + str(cur_cmd.next_command_operator) + " "
                cur_cmd = cur_cmd.next_command
            statement += output_statement(cur_cmd)
            cmd = cur_cmd.next_command
        else:
            statement = output_statement(cmd)
            cmd = cmd.next_command

        statements.append(statement)
    return statements

for statement in output_statements(first_cmd):
    print(statement)
