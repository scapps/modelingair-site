## In brief

We pursue efficient means of improving air quality. The group develops and applies sensitivity analysis methods in chemical transport models, including the hyperdual-step and adjoint approaches in CMAQ and GEOS-Chem, so that the influence of emissions on pollutant concentrations, health, and climate can be resolved exactly rather than approximated. We care about informative data visualization, and we build tools that other researchers and agencies can use.

## Numerically exact sensitivity analysis

Finite-difference and zero-out approaches to source attribution miss the nonlinear and cross terms that matter most in polluted, NOx-saturated air. We augmented CMAQ with hyperdual numbers to compute first- and second-order derivatives of concentrations with respect to emissions to machine precision, and extended the same idea to the global model as GEOS-Chem-hyd and to emissions handling through HEMCO-hyd. These models let us quantify, for example, how NOx and volatile chemical product emissions combine nonlinearly to form ozone and fine particles and how that translates into acute premature mortality.

## Aerosol thermodynamics

The group's methods lineage runs through ISORROPIA, the inorganic aerosol thermodynamic equilibrium model. We developed ANISORROPIA, its adjoint, and ISORROPIA-MCX, a multicomplex-variable version that enables sensitivity analysis of aerosol composition, and we have carried the model indoors to simulate inorganic aerosols of outdoor origin in buildings and air handling units.

## Satellites, data assimilation, and emissions

Satellite observations of trace gases constrain emissions when paired with a model that can be differentiated. Current work uses TEMPO nitrogen dioxide observations with hyperdual-enhanced data assimilation in GEOS-Chem to improve ozone estimates, and it uses CrIS-derived ammonia emissions to improve simulated nitrate and ammonium aerosol.

## Air quality and community health

Alongside the modeling, we work with Philadelphia communities to reduce residents' exposure to air pollution, including placing low-cost air cleaners and sensors in homes and connecting measurements with regulatory dispersion modeling through open-source tools such as pyAERMOD.
