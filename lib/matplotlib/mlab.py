"""
Numerical python functions written for compatibility with MATLAB
commands with the same names. Most numerical python functions can be found in
the `numpy` and `scipy` libraries. What remains here is code for performing
spectral computations.

Spectral functions
-------------------

`cohere`
    Coherence (normalized cross spectral density)

`csd`
    Cross spectral density using Welch's average periodogram

`detrend`
    Remove the mean or best fit line from an array

`psd`
    Power spectral density using Welch's average periodogram

`specgram`
    Spectrogram (spectrum over segments of time)

`complex_spectrum`
    Return the complex-valued frequency spectrum of a signal

`magnitude_spectrum`
    Return the magnitude of the frequency spectrum of a signal

`angle_spectrum`
    Return the angle (wrapped phase) of the frequency spectrum of a signal

`phase_spectrum`
    Return the phase (unwrapped angle) of the frequency spectrum of a signal

`detrend_mean`
    Remove the mean from a line.

`detrend_linear`
    Remove the best fit line from a line.

`detrend_none`
    Return the original line.

`stride_windows`
    Get all windows in an array in a memory-efficient manner

`stride_repeat`
    Repeat an array in a memory-efficient manner

`apply_window`
    Apply a window along a given axis
"""

import functools
from numbers import Number

import numpy as np

import matplotlib.cbook as cbook
from matplotlib import docstring


def window_hanning(x):
    """
    Return x times the hanning window of len(x).

    See Also
    --------
    window_none : Another window algorithm.
    """
    return np.hanning(len(x))*x


def window_none(x):
    """
    No window function; simply return x.

    See Also
    --------
    window_hanning : Another window algorithm.
    """
    return x


@cbook.deprecated("3.2")
def apply_window(x, window, axis=0, return_window=None):
    """
    Apply the given window to the given 1D or 2D array along the given axis.

    Parameters
    ----------
    x : 1D or 2D array or sequence
        Array or sequence containing the data.

    window : function or array.
        Either a function to generate a window or an array with length
        *x*.shape[*axis*]

    axis : int
        The axis over which to do the repetition.
        Must be 0 or 1.  The default is 0

    return_window : bool
        If true, also return the 1D values of the window that was applied
    """
    x = np.asarray(x)

    if x.ndim < 1 or x.ndim > 2:
        raise ValueError('only 1D or 2D arrays can be used')
    if axis+1 > x.ndim:
        raise ValueError('axis(=%s) out of bounds' % axis)

    xshape = list(x.shape)
    xshapetarg = xshape.pop(axis)

    if np.iterable(window):
        if len(window) != xshapetarg:
            raise ValueError('The len(window) must be the same as the shape '
                             'of x for the chosen axis')
        windowVals = window
    else:
        windowVals = window(np.ones(xshapetarg, dtype=x.dtype))

    if x.ndim == 1:
        if return_window:
            return windowVals * x, windowVals
        else:
            return windowVals * x

    xshapeother = xshape.pop()

    otheraxis = (axis+1) % 2

    windowValsRep = stride_repeat(windowVals, xshapeother, axis=otheraxis)

    if return_window:
        return windowValsRep * x, windowVals
    else:
        return windowValsRep * x


def detrend(x, key=None, axis=None):
    """
    Return x with its trend removed.

    Parameters
    ----------
    x : array or sequence
        Array or sequence containing the data.

    key : {'default', 'constant', 'mean', 'linear', 'none'} or function
        The detrending algorithm to use. 'default', 'mean', and 'constant' are
        the same as `detrend_mean`. 'linear' is the same as `detrend_linear`.
        'none' is the same as `detrend_none`. The default is 'mean'. See the
        corresponding functions for more details regarding the algorithms. Can
        also be a function that carries out the detrend operation.

    axis : int
        The axis along which to do the detrending.

    See Also
    --------
    detrend_mean : Implementation of the 'mean' algorithm.
    detrend_linear : Implementation of the 'linear' algorithm.
    detrend_none : Implementation of the 'none' algorithm.
    """
    if key is None or key in ['constant', 'mean', 'default']:
        return detrend(x, key=detrend_mean, axis=axis)
    elif key == 'linear':
        return detrend(x, key=detrend_linear, axis=axis)
    elif key == 'none':
        return detrend(x, key=detrend_none, axis=axis)
    elif callable(key):
        x = np.asarray(x)
        if axis is not None and axis + 1 > x.ndim:
            raise ValueError(f'axis(={axis}) out of bounds')
        if (axis is None and x.ndim == 0) or (not axis and x.ndim == 1):
            return key(x)
        # try to use the 'axis' argument if the function supports it,
        # otherwise use apply_along_axis to do it
        try:
            return key(x, axis=axis)
        except TypeError:
            return np.apply_along_axis(key, axis=axis, arr=x)
    else:
        raise ValueError(
            f"Unknown value for key: {key!r}, must be one of: 'default', "
            f"'constant', 'mean', 'linear', or a function")


def detrend_mean(x, axis=None):
    """
    Return x minus the mean(x).

    Parameters
    ----------
    x : array or sequence
        Array or sequence containing the data
        Can have any dimensionality

    axis : int
        The axis along which to take the mean.  See numpy.mean for a
        description of this argument.

    See Also
    --------
    detrend_linear : Another detrend algorithm.
    detrend_none : Another detrend algorithm.
    detrend : A wrapper around all the detrend algorithms.
    """
    x = np.asarray(x)

    if axis is not None and axis+1 > x.ndim:
        raise ValueError('axis(=%s) out of bounds' % axis)

    return x - x.mean(axis, keepdims=True)


def detrend_none(x, axis=None):
    """
    Return x: no detrending.

    Parameters
    ----------
    x : any object
        An object containing the data

    axis : int
        This parameter is ignored.
        It is included for compatibility with detrend_mean

    See Also
    --------
    detrend_mean : Another detrend algorithm.
    detrend_linear : Another detrend algorithm.
    detrend : A wrapper around all the detrend algorithms.
    """
    return x


def detrend_linear(y):
    """
    Return x minus best fit line; 'linear' detrending.

    Parameters
    ----------
    y : 0-D or 1-D array or sequence
        Array or sequence containing the data

    axis : int
        The axis along which to take the mean.  See numpy.mean for a
        description of this argument.

    See Also
    --------
    detrend_mean : Another detrend algorithm.
    detrend_none : Another detrend algorithm.
    detrend : A wrapper around all the detrend algorithms.
    """
    # This is faster than an algorithm based on linalg.lstsq.
    y = np.asarray(y)

    if y.ndim > 1:
        raise ValueError('y cannot have ndim > 1')

    # short-circuit 0-D array.
    if not y.ndim:
        return np.array(0., dtype=y.dtype)

    x = np.arange(y.size, dtype=float)

    C = np.cov(x, y, bias=1)
    b = C[0, 1]/C[0, 0]

    a = y.mean() - b*x.mean()
    return y - (b*x + a)


def stride_windows(x, n, noverlap=None, axis=0):
    """
    Get all windows of x with length n as a single array,
    using strides to avoid data duplication.

    .. warning::

        It is not safe to write to the output array.  Multiple
        elements may point to the same piece of memory,
        so modifying one value may change others.

    Parameters
    ----------
    x : 1D array or sequence
        Array or sequence containing the data.

    n : int
        The number of data points in each window.

    noverlap : int
        The overlap between adjacent windows.
        Default is 0 (no overlap)

    axis : int
        The axis along which the windows will run.

    References
    ----------
    `stackoverflow: Rolling window for 1D arrays in Numpy?
    <http://stackoverflow.com/a/6811241>`_
    `stackoverflow: Using strides for an efficient moving average filter
    <http://stackoverflow.com/a/4947453>`_
    """
    if noverlap is None:
        noverlap = 0

    if noverlap >= n:
        raise ValueError('noverlap must be less than n')
    if n < 1:
        raise ValueError('n cannot be less than 1')

    x = np.asarray(x)

    if x.ndim != 1:
        raise ValueError('only 1-dimensional arrays can be used')
    if n == 1 and noverlap == 0:
        if axis == 0:
            return x[np.newaxis]
        else:
            return x[np.newaxis].transpose()
    if n > x.size:
        raise ValueError('n cannot be greater than the length of x')

    # np.lib.stride_tricks.as_strided easily leads to memory corruption for
    # non integer shape and strides, i.e. noverlap or n. See #3845.
    noverlap = int(noverlap)
    n = int(n)

    step = n - noverlap
    if axis == 0:
        shape = (n, (x.shape[-1]-noverlap)//step)
        strides = (x.strides[0], step*x.strides[0])
    else:
        shape = ((x.shape[-1]-noverlap)//step, n)
        strides = (step*x.strides[0], x.strides[0])
    return np.lib.stride_tricks.as_strided(x, shape=shape, strides=strides)


@cbook.deprecated("3.2")
def stride_repeat(x, n, axis=0):
    """
    Repeat the values in an array in a memory-efficient manner.  Array x is
    stacked vertically n times.

    .. warning::

        It is not safe to write to the output array.  Multiple
        elements may point to the same piece of memory, so
        modifying one value may change others.

    Parameters
    ----------
    x : 1D array or sequence
        Array or sequence containing the data.

    n : int
        The number of time to repeat the array.

    axis : int
        The axis along which the data will run.

    References
    ----------
    `stackoverflow: Repeat NumPy array without replicating data?
    <http://stackoverflow.com/a/5568169>`_
    """
    if axis not in [0, 1]:
        raise ValueError('axis must be 0 or 1')
    x = np.asarray(x)
    if x.ndim != 1:
        raise ValueError('only 1-dimensional arrays can be used')

    if n == 1:
        if axis == 0:
            return np.atleast_2d(x)
        else:
            return np.atleast_2d(x).T
    if n < 1:
        raise ValueError('n cannot be less than 1')

    # np.lib.stride_tricks.as_strided easily leads to memory corruption for
    # non integer shape and strides, i.e. n. See #3845.
    n = int(n)

    if axis == 0:
        shape = (n, x.size)
        strides = (0, x.strides[0])
    else:
        shape = (x.size, n)
        strides = (x.strides[0], 0)

    return np.lib.stride_tricks.as_strided(x, shape=shape, strides=strides)


def _spectral_helper(x, y=None, NFFT=None, Fs=None, detrend_func=None,
                     window=None, noverlap=None, pad_to=None,
                     sides=None, scale_by_freq=None, mode=None):
    """
    This is a helper function that implements the commonality between the
    psd, csd, spectrogram and complex, magnitude, angle, and phase spectrums.
    It is *NOT* meant to be used outside of mlab and may change at any time.
    """
    if y is None:
        # if y is None use x for y
        same_data = True
    else:
        # The checks for if y is x are so that we can use the same function to
        # implement the core of psd(), csd(), and spectrogram() without doing
        # extra calculations.  We return the unaveraged Pxy, freqs, and t.
        same_data = y is x

    if Fs is None:
        Fs = 2
    if noverlap is None:
        noverlap = 0
    if detrend_func is None:
        detrend_func = detrend_none
    if window is None:
        window = window_hanning

    # if NFFT is set to None use the whole signal
    if NFFT is None:
        NFFT = 256

    if mode is None or mode == 'default':
        mode = 'psd'
    cbook._check_in_list(
        ['default', 'psd', 'complex', 'magnitude', 'angle', 'phase'],
        mode=mode)

    if not same_data and mode != 'psd':
        raise ValueError("x and y must be equal if mode is not 'psd'")

    # Make sure we're dealing with a numpy array. If y and x were the same
    # object to start with, keep them that way
    x = np.asarray(x)
    if not same_data:
        y = np.asarray(y)

    if sides is None or sides == 'default':
        if np.iscomplexobj(x):
            sides = 'twosided'
        else:
            sides = 'onesided'
    cbook._check_in_list(['default', 'onesided', 'twosided'], sides=sides)

    # zero pad x and y up to NFFT if they are shorter than NFFT
    if len(x) < NFFT:
        n = len(x)
        x = np.resize(x, NFFT)
        x[n:] = 0

    if not same_data and len(y) < NFFT:
        n = len(y)
        y = np.resize(y, NFFT)
        y[n:] = 0

    if pad_to is None:
        pad_to = NFFT

    if mode != 'psd':
        scale_by_freq = False
    elif scale_by_freq is None:
        scale_by_freq = True

    # For real x, ignore the negative frequencies unless told otherwise
    if sides == 'twosided':
        numFreqs = pad_to
        if pad_to % 2:
            freqcenter = (pad_to - 1)//2 + 1
        else:
            freqcenter = pad_to//2
        scaling_factor = 1.
    elif sides == 'onesided':
        if pad_to % 2:
            numFreqs = (pad_to + 1)//2
        else:
            numFreqs = pad_to//2 + 1
        scaling_factor = 2.

    if not np.iterable(window):
        window = window(np.ones(NFFT, x.dtype))
    if len(window) != NFFT:
        raise ValueError(
            "The window length must match the data's first dimension")

    result = stride_windows(x, NFFT, noverlap, axis=0)
    result = detrend(result, detrend_func, axis=0)
    result = result * window.reshape((-1, 1))
    result = np.fft.fft(result, n=pad_to, axis=0)[:numFreqs, :]
    freqs = np.fft.fftfreq(pad_to, 1/Fs)[:numFreqs]

    if not same_data:
        # if same_data is False, mode must be 'psd'
        resultY = stride_windows(y, NFFT, noverlap)
        resultY = detrend(resultY, detrend_func, axis=0)
        resultY = resultY * window.reshape((-1, 1))
        resultY = np.fft.fft(resultY, n=pad_to, axis=0)[:numFreqs, :]
        result = np.conj(result) * resultY
    elif mode == 'psd':
        result = np.conj(result) * result
    elif mode == 'magnitude':
        result = np.abs(result) / np.abs(window).sum()
    elif mode == 'angle' or mode == 'phase':
        # we unwrap the phase later to handle the onesided vs. twosided case
        result = np.angle(result)
    elif mode == 'complex':
        result /= np.abs(window).sum()

    if mode == 'psd':

        # Also include scaling factors for one-sided densities and dividing by
        # the sampling frequency, if desired. Scale everything, except the DC
        # component and the NFFT/2 component:

        # if we have a even number of frequencies, don't scale NFFT/2
        if not NFFT % 2:
            slc = slice(1, -1, None)
        # if we have an odd number, just don't scale DC
        else:
            slc = slice(1, None, None)

        result[slc] *= scaling_factor

        # MATLAB divides by the sampling frequency so that density function
        # has units of dB/Hz and can be integrated by the plotted frequency
        # values. Perform the same scaling here.
        if scale_by_freq:
            result /= Fs
            # Scale the spectrum by the norm of the window to compensate for
            # windowing loss; see Bendat & Piersol Sec 11.5.2.
            result /= (np.abs(window)**2).sum()
        else:
            # In this case, preserve power in the segment, not amplitude
            result /= np.abs(window).sum()**2

    t = np.arange(NFFT/2, len(x) - NFFT/2 + 1, NFFT - noverlap)/Fs

    if sides == 'twosided':
        # center the frequency range at zero
        freqs = np.concatenate((freqs[freqcenter:], freqs[:freqcenter]))
        result = np.concatenate((result[freqcenter:, :],
                                 result[:freqcenter, :]), 0)
    elif not pad_to % 2:
        # get the last value correctly, it is negative otherwise
        freqs[-1] *= -1

    # we unwrap the phase here to handle the onesided vs. twosided case
    if mode == 'phase':
        result = np.unwrap(result, axis=0)

    return result, freqs, t


def _single_spectrum_helper(
        mode, x, Fs=None, window=None, pad_to=None, sides=None):
    """
    This is a helper function that implements the commonality between the
    complex, magnitude, angle, and phase spectrums.
    It is *NOT* meant to be used outside of mlab and may change at any time.
    """
    cbook._check_in_list(['complex', 'magnitude', 'angle', 'phase'], mode=mode)

    if pad_to is None:
        pad_to = len(x)

    spec, freqs, _ = _spectral_helper(x=x, y=None, NFFT=len(x), Fs=Fs,
                                      detrend_func=detrend_none, window=window,
                                      noverlap=0, pad_to=pad_to,
                                      sides=sides,
                                      scale_by_freq=False,
                                      mode=mode)
    if mode != 'complex':
        spec = spec.real

    if spec.ndim == 2 and spec.shape[1] == 1:
        spec = spec[:, 0]

    return spec, freqs


# Split out these keyword docs so that they can be used elsewhere
docstring.interpd.update(
    Spectral="""\
Fs : scalar, default: 2
    The sampling frequency (samples per time unit).  It is used to calculate
    the Fourier frequencies, *freqs*, in cycles per time unit.

window : callable or ndarray, default: `.window_hanning`
    A function or a vector of length *NFFT*.  To create window vectors see
    `.window_hanning`, `.window_none`, `numpy.blackman`, `numpy.hamming`,
    `numpy.bartlett`, `scipy.signal`, `scipy.signal.get_window`, etc.  If a
    function is passed as the argument, it must take a data segment as an
    argument and return the windowed version of the segment.

sides : {'default', 'onesided', 'twosided'}, optional
    Which sides of the spectrum to return. 'default' is one-sided for real
    data and two-sided for complex data. 'onesided' forces the return of a
    one-sided spectrum, while 'twosided' forces two-sided.""",

    Single_Spectrum="""\
pad_to : int, optional
    The number of points to which the data segment is padded when performing
    the FFT.  While not increasing the actual resolution of the spectrum (the
    minimum distance between resolvable peaks), this can give more points in
    the plot, allowing for more detail. This corresponds to the *n* parameter
    in the call to fft().  The default is None, which sets *pad_to* equal to
    the length of the input signal (i.e. no padding).""",

    PSD="""\
pad_to : int, optional
    The number of points to which the data segment is padded when performing
    the FFT.  This can be different from *NFFT*, which specifies the number
    of data points used.  While not increasing the actual resolution of the
    spectrum (the minimum distance between resolvable peaks), this can give
    more points in the plot, allowing for more detail. This corresponds to
    the *n* parameter in the call to fft(). The default is None, which sets
    *pad_to* equal to *NFFT*

NFFT : int, default: 256
    The number of data points used in each block for the FFT.  A power 2 is
    most efficient.  This should *NOT* be used to get zero padding, or the
    scaling of the result will be incorrect; use *pad_to* for this instead.

detrend : {'none', 'mean', 'linear'} or callable, default 'none'
    The function applied to each segment before fft-ing, designed to remove
    the mean or linear trend.  Unlike in MATLAB, where the *detrend* parameter
    is a vector, in Matplotlib is it a function.  The :mod:`~matplotlib.mlab`
    module defines `.detrend_none`, `.detrend_mean`, and `.detrend_linear`,
    but you can use a custom function as well.  You can also use a string to
    choose one of the functions: 'none' calls `.detrend_none`. 'mean' calls
    `.detrend_mean`. 'linear' calls `.detrend_linear`.

scale_by_freq : bool, optional, default: True
    Whether the resulting density values should be scaled by the scaling
    frequency, which gives density in units of Hz^-1.  This allows for
    integration over the returned frequency values.  The default is True for
    MATLAB compatibility.""")


@docstring.dedent_interpd
def psd(x, NFFT=None, Fs=None, detrend=None, window=None,
        noverlap=None, pad_to=None, sides=None, scale_by_freq=None):
    r"""
    Compute the power spectral density.

    The power spectral density :math:`P_{xx}` by Welch's average
    periodogram method.  The vector *x* is divided into *NFFT* length
    segments.  Each segment is detrended by function *detrend* and
    windowed by function *window*.  *noverlap* gives the length of
    the overlap between segments.  The :math:`|\mathrm{fft}(i)|^2`
    of each segment :math:`i` are averaged to compute :math:`P_{xx}`.

    If len(*x*) < *NFFT*, it will be zero padded to *NFFT*.

    Parameters
    ----------
    x : 1-D array or sequence
        Array or sequence containing the data

    %(Spectral)s

    %(PSD)s

    noverlap : int
        The number of points of overlap between segments.
        The default value is 0 (no overlap).

    Returns
    -------
    Pxx : 1-D array
        The values for the power spectrum :math:`P_{xx}` (real valued)

    freqs : 1-D array
        The frequencies corresponding to the elements in *Pxx*

    References
    ----------
    Bendat & Piersol -- Random Data: Analysis and Measurement Procedures, John
    Wiley & Sons (1986)

    See Also
    --------
    specgram
        `specgram` differs in the default overlap; in not returning the mean of
        the segment periodograms; and in returning the times of the segments.

    magnitude_spectrum : returns the magnitude spectrum.

    csd : returns the spectral density between two signals.
    """
    Pxx, freqs = csd(x=x, y=None, NFFT=NFFT, Fs=Fs, detrend=detrend,
                     window=window, noverlap=noverlap, pad_to=pad_to,
                     sides=sides, scale_by_freq=scale_by_freq)
    return Pxx.real, freqs


@docstring.dedent_interpd
def csd(x, y, NFFT=None, Fs=None, detrend=None, window=None,
        noverlap=None, pad_to=None, sides=None, scale_by_freq=None):
    """
    Compute the cross-spectral density.

    The cross spectral density :math:`P_{xy}` by Welch's average
    periodogram method.  The vectors *x* and *y* are divided into
    *NFFT* length segments.  Each segment is detrended by function
    *detrend* and windowed by function *window*.  *noverlap* gives
    the length of the overlap between segments.  The product of
    the direct FFTs of *x* and *y* are averaged over each segment
    to compute :math:`P_{xy}`, with a scaling to correct for power
    loss due to windowing.

    If len(*x*) < *NFFT* or len(*y*) < *NFFT*, they will be zero
    padded to *NFFT*.

    Parameters
    ----------
    x, y : 1-D arrays or sequences
        Arrays or sequences containing the data

    %(Spectral)s

    %(PSD)s

    noverlap : int
        The number of points of overlap between segments.
        The default value is 0 (no overlap).

    Returns
    -------
    Pxy : 1-D array
        The values for the cross spectrum :math:`P_{xy}` before scaling (real
        valued)

    freqs : 1-D array
        The frequencies corresponding to the elements in *Pxy*

    References
    ----------
    Bendat & Piersol -- Random Data: Analysis and Measurement Procedures, John
    Wiley & Sons (1986)

    See Also
    --------
    psd : equivalent to setting ``y = x``.
    """
    if NFFT is None:
        NFFT = 256
    Pxy, freqs, _ = _spectral_helper(x=x, y=y, NFFT=NFFT, Fs=Fs,
                                     detrend_func=detrend, window=window,
                                     noverlap=noverlap, pad_to=pad_to,
                                     sides=sides, scale_by_freq=scale_by_freq,
                                     mode='psd')

    if Pxy.ndim == 2:
        if Pxy.shape[1] > 1:
            Pxy = Pxy.mean(axis=1)
        else:
            Pxy = Pxy[:, 0]
    return Pxy, freqs


_single_spectrum_docs = """\
Compute the {quantity} of *x*.
Data is padded to a length of *pad_to* and the windowing function *window* is
applied to the signal.

Parameters
----------
x : 1-D array or sequence
    Array or sequence containing the data

{Spectral}

{Single_Spectrum}

Returns
-------
spectrum : 1-D array
    The {quantity}.
freqs : 1-D array
    The frequencies corresponding to the elements in *spectrum*.

See Also
--------
psd
    Returns the power spectral density.
complex_spectrum
    Returns the complex-valued frequency spectrum.
magnitude_spectrum
    Returns the absolute value of the `complex_spectrum`.
angle_spectrum
    Returns the angle of the `complex_spectrum`.
phase_spectrum
    Returns the phase (unwrapped angle) of the `complex_spectrum`.
specgram
    Can return the complex spectrum of segments within the signal.
"""


complex_spectrum = functools.partial(_single_spectrum_helper, "complex")
complex_spectrum.__doc__ = _single_spectrum_docs.format(
    quantity="complex-valued frequency spectrum",
    **docstring.interpd.params)
magnitude_spectrum = functools.partial(_single_spectrum_helper, "magnitude")
magnitude_spectrum.__doc__ = _single_spectrum_docs.format(
    quantity="magnitude (absolute value) of the frequency spectrum",
    **docstring.interpd.params)
angle_spectrum = functools.partial(_single_spectrum_helper, "angle")
angle_spectrum.__doc__ = _single_spectrum_docs.format(
    quantity="angle of the frequency spectrum (wrapped phase spectrum)",
    **docstring.interpd.params)
phase_spectrum = functools.partial(_single_spectrum_helper, "phase")
phase_spectrum.__doc__ = _single_spectrum_docs.format(
    quantity="phase of the frequency spectrum (unwrapped phase spectrum)",
    **docstring.interpd.params)


@docstring.dedent_interpd
def specgram(x, NFFT=None, Fs=None, detrend=None, window=None,
             noverlap=None, pad_to=None, sides=None, scale_by_freq=None,
             mode=None):
    """
    Compute a spectrogram.

    Compute and plot a spectrogram of data in x.  Data are split into
    NFFT length segments and the spectrum of each section is
    computed.  The windowing function window is applied to each
    segment, and the amount of overlap of each segment is
    specified with noverlap.

    Parameters
    ----------
    x : array-like
        1-D array or sequence.

    %(Spectral)s

    %(PSD)s

    noverlap : int, optional
        The number of points of overlap between blocks.  The default
        value is 128.
    mode : str, optional, default: 'psd'
        What sort of spectrum to use:
            'psd'
                Returns the power spectral density.
            'complex'
                Returns the complex-valued frequency spectrum.
            'magnitude'
                Returns the magnitude spectrum.
            'angle'
                Returns the phase spectrum without unwrapping.
            'phase'
                Returns the phase spectrum with unwrapping.

    Returns
    -------
    spectrum : array-like
        2-D array, columns are the periodograms of successive segments.

    freqs : array-like
        1-D array, frequencies corresponding to the rows in *spectrum*.

    t : array-like
        1-D array, the times corresponding to midpoints of segments
        (i.e the columns in *spectrum*).

    See Also
    --------
    psd : differs in the overlap and in the return values.
    complex_spectrum : similar, but with complex valued frequencies.
    magnitude_spectrum : similar single segment when mode is 'magnitude'.
    angle_spectrum : similar to single segment when mode is 'angle'.
    phase_spectrum : similar to single segment when mode is 'phase'.

    Notes
    -----
    detrend and scale_by_freq only apply when *mode* is set to 'psd'.

    """
    if noverlap is None:
        noverlap = 128  # default in _spectral_helper() is noverlap = 0
    if NFFT is None:
        NFFT = 256  # same default as in _spectral_helper()
    if len(x) <= NFFT:
        cbook._warn_external("Only one segment is calculated since parameter "
                             "NFFT (=%d) >= signal length (=%d)." %
                             (NFFT, len(x)))

    spec, freqs, t = _spectral_helper(x=x, y=None, NFFT=NFFT, Fs=Fs,
                                      detrend_func=detrend, window=window,
                                      noverlap=noverlap, pad_to=pad_to,
                                      sides=sides,
                                      scale_by_freq=scale_by_freq,
                                      mode=mode)

    if mode != 'complex':
        spec = spec.real  # Needed since helper implements generically

    return spec, freqs, t


@docstring.dedent_interpd
def cohere(x, y, NFFT=256, Fs=2, detrend=detrend_none, window=window_hanning,
           noverlap=0, pad_to=None, sides='default', scale_by_freq=None):
    r"""
    The coherence between *x* and *y*.  Coherence is the normalized
    cross spectral density:

    .. math::

        C_{xy} = \frac{|P_{xy}|^2}{P_{xx}P_{yy}}

    Parameters
    ----------
    x, y
        Array or sequence containing the data

    %(Spectral)s

    %(PSD)s

    noverlap : int
        The number of points of overlap between blocks.  The default value
        is 0 (no overlap).

    Returns
    -------
    The return value is the tuple (*Cxy*, *f*), where *f* are the
    frequencies of the coherence vector. For cohere, scaling the
    individual densities by the sampling frequency has no effect,
    since the factors cancel out.

    See Also
    --------
    :func:`psd`, :func:`csd` :
        For information about the methods used to compute :math:`P_{xy}`,
        :math:`P_{xx}` and :math:`P_{yy}`.
    """
    if len(x) < 2 * NFFT:
        raise ValueError(
            "Coherence is calculated by averaging over *NFFT* length "
            "segments.  Your signal is too short for your choice of *NFFT*.")
    Pxx, f = psd(x, NFFT, Fs, detrend, window, noverlap, pad_to, sides,
                 scale_by_freq)
    Pyy, f = psd(y, NFFT, Fs, detrend, window, noverlap, pad_to, sides,
                 scale_by_freq)
    Pxy, f = csd(x, y, NFFT, Fs, detrend, window, noverlap, pad_to, sides,
                 scale_by_freq)
    Cxy = np.abs(Pxy) ** 2 / (Pxx * Pyy)
    return Cxy, f


class GaussianKDE:
    """
    Representation of a kernel-density estimate using Gaussian kernels.

    Parameters
    ----------
    dataset : array-like
        Datapoints to estimate from. In case of univariate data this is a 1-D
        array, otherwise a 2-D array with shape (# of dims, # of data).

    bw_method : str, scalar or callable, optional
        The method used to calculate the estimator bandwidth.  This can be
        'scott', 'silverman', a scalar constant or a callable.  If a
        scalar, this will be used directly as `kde.factor`.  If a
        callable, it should take a `GaussianKDE` instance as only
        parameter and return a scalar. If None (default), 'scott' is used.

    Attributes
    ----------
    dataset : ndarray
        The dataset with which `gaussian_kde` was initialized.

    dim : int
        Number of dimensions.

    num_dp : int
        Number of datapoints.

    factor : float
        The bandwidth factor, obtained from `kde.covariance_factor`, with which
        the covariance matrix is multiplied.

    covariance : ndarray
        The covariance matrix of *dataset*, scaled by the calculated bandwidth
        (`kde.factor`).

    inv_cov : ndarray
        The inverse of *covariance*.

    Methods
    -------
    kde.evaluate(points) : ndarray
        Evaluate the estimated pdf on a provided set of points.

    kde(points) : ndarray
        Same as kde.evaluate(points)

    """

    # This implementation with minor modification was too good to pass up.
    # from scipy: https://github.com/scipy/scipy/blob/master/scipy/stats/kde.py

    def __init__(self, dataset, bw_method=None):
        self.dataset = np.atleast_2d(dataset)
        if not np.array(self.dataset).size > 1:
            raise ValueError("`dataset` input should have multiple elements.")

        self.dim, self.num_dp = np.array(self.dataset).shape

        if bw_method is None:
            pass
        elif cbook._str_equal(bw_method, 'scott'):
            self.covariance_factor = self.scotts_factor
        elif cbook._str_equal(bw_method, 'silverman'):
            self.covariance_factor = self.silverman_factor
        elif isinstance(bw_method, Number):
            self._bw_method = 'use constant'
            self.covariance_factor = lambda: bw_method
        elif callable(bw_method):
            self._bw_method = bw_method
            self.covariance_factor = lambda: self._bw_method(self)
        else:
            raise ValueError("`bw_method` should be 'scott', 'silverman', a "
                             "scalar or a callable")

        # Computes the covariance matrix for each Gaussian kernel using
        # covariance_factor().

        self.factor = self.covariance_factor()
        # Cache covariance and inverse covariance of the data
        if not hasattr(self, '_data_inv_cov'):
            self.data_covariance = np.atleast_2d(
                np.cov(
                    self.dataset,
                    rowvar=1,
                    bias=False))
            self.data_inv_cov = np.linalg.inv(self.data_covariance)

        self.covariance = self.data_covariance * self.factor ** 2
        self.inv_cov = self.data_inv_cov / self.factor ** 2
        self.norm_factor = (np.sqrt(np.linalg.det(2 * np.pi * self.covariance))
                            * self.num_dp)

    def scotts_factor(self):
        return np.power(self.num_dp, -1. / (self.dim + 4))

    def silverman_factor(self):
        return np.power(
            self.num_dp * (self.dim + 2.0) / 4.0, -1. / (self.dim + 4))

    #  Default method to calculate bandwidth, can be overwritten by subclass
    covariance_factor = scotts_factor

    def evaluate(self, points):
        """Evaluate the estimated pdf on a set of points.

        Parameters
        ----------
        points : (# of dimensions, # of points)-array
            Alternatively, a (# of dimensions,) vector can be passed in and
            treated as a single point.

        Returns
        -------
        values : (# of points,)-array
            The values at each point.

        Raises
        ------
        ValueError : if the dimensionality of the input points is different
                     than the dimensionality of the KDE.

        """
        points = np.atleast_2d(points)

        dim, num_m = np.array(points).shape
        if dim != self.dim:
            raise ValueError("points have dimension {}, dataset has dimension "
                             "{}".format(dim, self.dim))

        result = np.zeros(num_m)

        if num_m >= self.num_dp:
            # there are more points than data, so loop over data
            for i in range(self.num_dp):
                diff = self.dataset[:, i, np.newaxis] - points
                tdiff = np.dot(self.inv_cov, diff)
                energy = np.sum(diff * tdiff, axis=0) / 2.0
                result = result + np.exp(-energy)
        else:
            # loop over points
            for i in range(num_m):
                diff = self.dataset - points[:, i, np.newaxis]
                tdiff = np.dot(self.inv_cov, diff)
                energy = np.sum(diff * tdiff, axis=0) / 2.0
                result[i] = np.sum(np.exp(-energy), axis=0)

        result = result / self.norm_factor

        return result

    __call__ = evaluate
