"""Run: python main.py --demo (no hardware needed)."""
import argparse


def main():
    parser = argparse.ArgumentParser(description="AMR ESP-NOW control through an ESP32 USB gateway")
    parser.add_argument("--demo", action="store_true", help="Automatically connect the simulator")
    args = parser.parse_args()
    try:
        import tkinter as tk
        from gui import App
    except ImportError as exc:
        raise SystemExit("Cần Python có Tkinter. Windows: cài Python với Tcl/Tk; Ubuntu: python3-tk.\n" + str(exc))
    root = tk.Tk()
    App(root, demo=args.demo)
    root.mainloop()


if __name__ == "__main__":
    main()
