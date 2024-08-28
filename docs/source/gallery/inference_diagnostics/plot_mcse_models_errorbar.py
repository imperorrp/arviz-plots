"""
# MCSE comparison plot with errorbars

Full MCSE comparison between different models with errorbars

---

:::{seealso}
API Documentation: {func}`~arviz_plots.plot_mcse`
:::
"""

from arviz_base import load_arviz_data

import arviz_plots as azp

azp.style.use("arviz-clean")

c = load_arviz_data("centered_eight")
n = load_arviz_data("non_centered_eight")
pc = azp.plot_mcse(
    {"Centered": c, "Non Centered": n},
    errorbar=True,
    backend="none",  # change to preferred backend
)
pc.show()
