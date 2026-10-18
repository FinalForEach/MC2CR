import multiprocessing

from mc2cr.cli import main

if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()
