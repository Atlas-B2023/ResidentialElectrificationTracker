import customtkinter as ctk

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import threading

ctk.set_appearance_mode("Light")  # Modes: "System" (standard), "Dark", "Light"
ctk.set_default_color_theme("blue")  # Themes: "blue" (standard), "green", "dark-blue"


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.buoot = ctk.CTkButton(self, text="hi")
        self.buoot.pack()
        threading.Thread(target=self.slow_load_figure).start()

    def slow_load_figure(self):
        frameChartsLT = ctk.CTkFrame(self)
        frameChartsLT.pack()

        stockListExp = ["AMZN", "AAPL", "JETS", "CCL", "NCLH"]
        stockSplitExp = [15, 25, 40, 10, 10]

        fig = Figure(facecolor="blue")  # create a figure object
        ax = fig.add_subplot(111)  # add an Axes to the figure
        ax.pie(
            stockSplitExp,
            radius=1,
            labels=stockListExp,
            autopct="%0.2f%%",
            shadow=False,
        )
        chart1 = FigureCanvasTkAgg(fig, frameChartsLT)
        chart1.get_tk_widget().pack()


if __name__ == "__main__":
    thing = App()
    thing.mainloop()
