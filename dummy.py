import select
import sys

exit_code = int(sys.argv[1])
exit_string = "success" if exit_code == 0 else "failure"
identifier = sys.argv[2]

if len(sys.argv) >= 4:
    import time
    time.sleep(int(sys.argv[3]))

rfds, _1, _2 = select.select([sys.stdin], [], [], 2)
if sys.stdin in rfds:
    pipe_text = sys.stdin.readline().strip()
else:
    pipe_text = ""

if pipe_text:
    sys.stdout.write("{0}: {1}, found: {2}\n".format(identifier, exit_string, repr(pipe_text)))
else:
    sys.stdout.write("{0}: {1}\n".format(identifier, exit_string))
sys.stdout.flush()

sys.exit(exit_code)
