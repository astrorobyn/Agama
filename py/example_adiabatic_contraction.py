'''
Module for performing adiabatic contraction of dark matter (DM) halo due to baryons.
Two methods are implemented:
(1) `true' adiabatic contraction relies on the invariance of actions under slow changes of potential:
    first the DM distribution function corresponding to the given density/potential profile is constructed,
    then the DM-only potential is replaced with the sum of DM+baryonic potentials,
    and the DM density profile generated by the DF in the new potential is computed.
(2) `approximate' prescription for contraction, which uses empirical correction formula calibrated
    against N-body simulations to transform the initial DM density into the contracted one
    without explicitly working with the DF.
    A Milky Way potential corresponding to an adiabatically contracted NFW halo is provided in
    ../data/Cautun20.ini

The routine `contraction()' performs either of the two procedures for the given DM and baryon profiles.
When run as the main program, this script uses the above routine to illustrate both methods.

Authors: Tom Callingham, Marius Cautun, Tadafumi Matsuno, Eugene Vasiliev
Date: Nov 2021
'''
import numpy, agama

def contraction(pot_dm, pot_bar, method='C20', beta_dm=0.0, rmin=1e-2, rmax=1e4):
    '''
    Construct the contracted halo density profile for the given
    initial halo density and the baryonic density profiles.
    Arguments:
      pot_dm:  initial halo potential (assumed to be spherical!).
      pot_bar: potential of baryons (a spherical approximation to it will be used even if it was not spherical).
      method:  choice between two alternative approaches:
        'C20'  (default) uses the approximate correction procedure from Cautun+2020;
        'adiabatic'  uses the invariance of actions in conjunction with an internally constructed halo DF.
      beta_dm: anisotropy coefficient for the halo DF
        (only used with the adiabatic method, must be between -0.5 and 1, default 0 means isotropy).
      rmin (1e-2), rmax(1e4): min/max grid radii for representing the contracted density profile
        (default values are suitable for Milky Way-sized galaxies if expressed in kpc).
    Return:
      the spherically symmetric contracted halo potential.
    '''
    gridr = numpy.logspace(numpy.log10(rmin), numpy.log10(rmax), 101)
    xyz = numpy.column_stack((gridr, gridr*0, gridr*0))
    if method == 'adiabatic':
        # create a spherical DF for the DM-only potential/density pair with a constant anisotropy coefficient beta
        df_dm = agama.DistributionFunction(type='QuasiSpherical', potential=pot_dm, beta0=beta_dm)
        # create a sphericalized total potential (DM+baryons)
        pot_total_sph = agama.Potential(type='multipole', potential=agama.Potential(pot_dm, pot_bar),
            lmax=0, rmin=0.1*rmin, rmax=10*rmax)
        # compute the density generated by the DF in the new total potential at the radial grid
        dens_contracted = agama.GalaxyModel(pot_total_sph, df_dm).moments(xyz, dens=True, vel=False, vel2=False)
    elif method == 'C20':
        # use the differential (d/dr) form of Eq. (11) from Cautun et al (2020) to approximate the effect of contraction
        cumul_mass_dm = pot_dm. enclosedMass(gridr)  # cumulative mass profile of DM
        cumul_mass_bar= pot_bar.enclosedMass(gridr)  # same for baryons (sphericalized)
        valid_r = numpy.hstack([True, cumul_mass_bar[:-1] < cumul_mass_bar[1:]*0.999])  # use only those radii where mass keeps increasing
        sph_dens_bar  = agama.Density(cumulmass=numpy.column_stack((gridr[valid_r], cumul_mass_bar[valid_r])))  # sphericalized baryon density profile
        f_bar = 0.157  # cosmic baryon fraction; the formula is calibrated against simulations only for this value
        eta_bar = cumul_mass_bar / cumul_mass_dm * (1.-f_bar) / f_bar  # the last two terms account for transforming the DM mass into the corresponding baryonic mass in dark-matter-only simulations
        first_factor = 0.45 + 0.41 * (eta_bar + 0.98)**0.53
        dens_dm_orig = pot_dm.density(xyz)
        temp         = sph_dens_bar.density(xyz) - eta_bar * dens_dm_orig * f_bar / (1.-f_bar)
        const_term   = 0.41 * 0.53 * (eta_bar + 0.98)**(0.53-1.) * (1.-f_bar) / f_bar * temp
        dens_contracted = dens_dm_orig * first_factor + const_term  # new values of DM density at the radial grid
    else:
        raise RuntimeError('Invalid choice of method')

    # create a cubic spline interpolator in log-log space
    valid_r = dens_contracted>0  # make sure the input for log-spline is positive
    dens_contracted_interp = agama.CubicSpline(numpy.log(gridr[valid_r]), numpy.log(dens_contracted[valid_r]), reg=True)
    # convert the grid-based density profile into a full-fledged potential
    contracted_pot = agama.Potential(type="Multipole", symmetry="spherical", rmin=rmin, rmax=rmax,
        density=lambda xyz: numpy.exp(dens_contracted_interp(numpy.log(numpy.sum(xyz**2, axis=1))*0.5)) )
    return contracted_pot


if __name__ == '__main__':
    # example of usage of the above function for the Milky Way potential from Cautun+ 2020
    agama.setUnits(mass=1., length=1., velocity=1.)  # Msun, kpc, km/s
    # DM halo
    fb = 4.825 / 30.7  # Planck 1 baryon fraction
    m200 = 0.969e12  # the DM halo mass
    conc = 8.76
    NFW_rho0 = 3486926.735447284
    NFW_rs = 25.20684733101539
    # Note subtletly in Cautun20 NFW definition, scaled overdensity changes from paper value!

    # bulge
    params_bulge = dict(type='Spheroid',
        densityNorm=1.03e11,
        axisRatioZ=0.5,
        gamma=0,
        beta=1.8,
        scaleRadius=0.075,
        outerCutoffRadius=2.1)
    # stellar disks
    params_thin_disk = dict(type='Disk',
        surfaceDensity=7.31e8,
        scaleRadius=2.63,
        scaleHeight=0.3)
    params_thick_disk = dict(type='Disk',
        surfaceDensity=1.01e8,
        scaleRadius=3.8,
        scaleHeight=0.9)
    # gas disks
    params_HI_disk = dict(type='disk',
        surfaceDensity=5.3e7,
        scaleRadius=7.0,
        scaleHeight=0.085,
        innerCutoffRadius=4.0)
    params_H2_disk = dict(type='disk',
        surfaceDensity=2.2e9,
        scaleRadius=1.5,
        scaleHeight=0.045,
        innerCutoffRadius=12.0)
    # CGM
    params_CGM = dict(type='Spheroid',
        densityNorm=7.615e2,
        gamma=1.46,
        beta=1.46,
        scaleRadius=219,
        outerCutoffRadius=2*219,
        cutoffStrength=2)
    # uncontracted DM halo
    params_halo = dict(type='Spheroid',
        densityNorm=3.487e6,
        gamma=1,
        beta=3,
        scaleRadius=25.2)

    pot_baryon = agama.Potential(params_bulge, params_thin_disk, params_thick_disk, params_HI_disk, params_H2_disk, params_CGM)
    pot_dm_init= agama.Potential(params_halo)
    # several variants of contracted halo potentials
    pot_dm_C20 = contraction(pot_dm_init, pot_baryon, method='C20')
    pot_dm_iso = contraction(pot_dm_init, pot_baryon, method='adiabatic', beta_dm= 0.0)
    pot_dm_rad = contraction(pot_dm_init, pot_baryon, method='adiabatic', beta_dm=+0.5)
    pot_dm_tan = contraction(pot_dm_init, pot_baryon, method='adiabatic', beta_dm=-0.5)
    # plot profiles
    import numpy, matplotlib.pyplot as plt
    r = numpy.logspace(-2,3,101)
    xyz = numpy.column_stack((r, r*0, r*0))
    ax = plt.subplots(1, 2, figsize=(10,5))[1]
    pots  = [pot_baryon, pot_dm_init, pot_dm_C20, pot_dm_iso, pot_dm_rad, pot_dm_tan]
    names = ['baryons', 'initial halo', 'contracted Cautun+2020', 'contracted isotropic', 'contracted radial', 'contracted tangential']
    colors= ['k', 'c', 'g', 'm', 'r', 'b']
    dashes= [[1000,1], [2,2], [5,2], [4,1,1,1], [7,3,2,3], [2,1,1,1]]
    for pot, name, color, dash in zip(pots, names, colors, dashes):
        ax[0].plot(r, pot.density(xyz),  label=name, color=color, dashes=dash)
        ax[1].plot(r, (-r*pot.force(xyz)[:,0])**0.5, color=color, dashes=dash)
    ax[0].set_xscale('log')
    ax[0].set_yscale('log')
    ax[1].set_xscale('log')
    ax[0].legend(loc='lower left', frameon=False)
    ax[0].set_xlabel('R [kpc]')
    ax[0].set_ylabel(r'$\rho\; \rm[M_\odot/kpc^3]$', fontsize=15)
    ax[1].set_xlabel('R [kpc]')
    ax[1].set_ylabel(r'$v_{\rm circ}\; \rm[km/s]$', fontsize=15)
    plt.tight_layout()
    plt.savefig('example_adiabatic_contraction.pdf')
    plt.show()
