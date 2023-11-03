import customtkinter as Ctk

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

Ctk.set_appearance_mode("Light")  # Modes: "System" (standard), "Dark", "Light"
Ctk.set_default_color_theme("blue")  # Themes: "blue" (standard), "green", "dark-blue"


class App(Ctk.CTk):
    def __init__(self):
        super().__init__()

        frameChartsLT = Ctk.CTkFrame(self)
        frameChartsLT.pack()

        stockListExp = ["AMZN", "AAPL", "JETS", "CCL", "NCLH"]
        stockSplitExp = [15, 25, 40, 10, 10]

        fig = Figure(facecolor="blue")  # create a figure object
        ax = fig.add_subplot(111)  # add an Axes to the figure
        ax.set_facecolor((0.5, 0.5, 0.5, 0.5))
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
