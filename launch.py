import sys
import os


if __name__ == '__main__':
    sys.path.append(os.path.dirname(__file__))
    import buganime
    buganime.buganime.main(sys.argv[1:])
