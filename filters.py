import warnings
import xarray
import scipy.signal
import numpy as np

try:
    from scipy.signal import sosfiltfilt
except ImportError:
    sosfiltfilt = None

from .utils import get_maybe_last_dim_axis, get_sampling_step

def _firwin_ba(*args, **kwargs):
    if not kwargs.get('pass_zero'):
        args = (args[0] + 1,) + args[1:]  # numtaps must be odd
    return scipy.signal.firwin(*args, **kwargs), np.array([1])


_BA_FUNCS = {
    'iir': scipy.signal.iirfilter,
    'fir': _firwin_ba,
    }

_ORDER_DEFAULTS = {
    'iir': 4,
    'fir': 29,
    }


def frequency_filter(darray, f_crit, order=None, irtype='iir', filtfilt=True,
                     apply_kwargs=None, in_nyq=False, dim=None, **kwargs):
    if irtype not in _BA_FUNCS:
        raise ValueError('Wrong argument for irtype: {}, must be one of {}'.format(
            irtype, _BA_FUNCS.keys()))
    if order is None:
        order = _ORDER_DEFAULTS[irtype]
    if apply_kwargs is None:
        apply_kwargs = {}
    dim, axis = get_maybe_last_dim_axis(darray, dim)
    f_crit_norm = np.asarray(f_crit, dtype=np.float)
    if not in_nyq:              # normalize by Nyquist frequency
        f_crit_norm *= 2 * get_sampling_step(darray, dim)
    order_corr = order // (2 if filtfilt else 1) # filtfilt -> double order
    data = np.asarray(darray)
    if sosfiltfilt and irtype == 'iir': # TODO merge with other if branch
        sos = scipy.signal.iirfilter(order_corr, f_crit_norm, output='sos', **kwargs)
        if filtfilt:
            data = sosfiltfilt(sos, data, axis, **apply_kwargs)
        else:
            data = scipy.signal.sosfilt(sos, data, axis, **apply_kwargs)
    else:
        b, a = _BA_FUNCS[irtype](order_corr, f_crit_norm, **kwargs)
        if filtfilt:
            data = scipy.signal.filtfilt(b, a, data, axis, **apply_kwargs)
        else:
            data = scipy.signal.lfilter(b, a, data, axis, **apply_kwargs)
    return darray.__array_wrap__(data)


def _update_ftype_kwargs(kwargs, iirvalue, firvalue):
    if kwargs.get('irtype', 'iir') == 'iir':
        kwargs.setdefault('btype', iirvalue)
    else:                       # fir
        kwargs.setdefault('pass_zero', firvalue)
    return kwargs


def lowpass(darray, f_cutoff, *args, **kwargs):
    kwargs = _update_ftype_kwargs(kwargs, 'lowpass', True)
    return frequency_filter(darray, f_cutoff, *args, **kwargs)


def highpass(darray, f_cutoff, *args, **kwargs):
    kwargs = _update_ftype_kwargs(kwargs, 'highpass', False)
    return frequency_filter(darray, f_cutoff, *args, **kwargs)


def bandpass(darray, f_low, f_high, *args, **kwargs):
    kwargs = _update_ftype_kwargs(kwargs, 'bandpass', False)
    return frequency_filter(darray, [f_low, f_high], *args, **kwargs)


class DecimationWarning(Warning):
    pass
# always (not just once) show decimation warnings to see the responsible signal
warnings.filterwarnings('always', category=DecimationWarning)

def decimate(darray, q=None, target_fs=None, dim=None, **lowpass_kwargs):
    '''Decimate signal by given (int) factor or to closest possible target_fs

    along the specified dimension

    Decimation: lowpass to new nyquist frequency and then downsample by factor q
    lowpass_kwargs are given to the lowpass method

    If q is not given, it is approximated as the closest integer ratio
    of fs / target_fs, so target_fs must be smaller than current sampling frequency fs

    If q < 2, decimation is skipped and a DecimationWarning is emitted
    '''
    dim, axis = get_maybe_last_dim_axis(darray, dim)
    if q is None:
        if target_fs is None:
            raise ValueError('either q or target_fs must be given')
        dt = get_sampling_step(darray, dim)
        q = int(np.rint(1.0 / (dt * target_fs)))
    if q < 2:                   # decimation not possible or useless
        # show warning at caller level to see which signal it is related to
        warnings.warn('q factor %i < 2, skipping decimation' % q,
                      DecimationWarning, stacklevel=2)
        return darray
    new_f_nyq = 1.0 / q
    lowpass_kwargs.setdefault('dim', dim)
    lowpass_kwargs.setdefault('in_nyq', True)
    ret = lowpass(darray, new_f_nyq, **lowpass_kwargs)
    ret = ret.isel(**{dim: slice(None, None, q)})
    return ret


def medfilt(darray, kernel_size=None):
    ret = scipy.signal.medfilt(np.asarray(darray), kernel_size)
    return darray.__array_wrap__(ret)


def wiener(darray, window_length, noise_variance=None, in_points=False, dim=None):
    if not in_points:
        delta = get_sampling_step(darray, dim)
        window_length = int(np.rint(window_length / delta))
    ret = scipy.signal.wiener(darray.values, window_length, noise_variance)
    return darray.__array_wrap__(ret)



def savgol_filter(darray, window_length, polyorder, deriv=0, delta=None,
                  dim=None, mode='interp', cval=0.0):
    dim, axis = get_maybe_last_dim_axis(darray, dim)
    if delta is None:
        delta = get_sampling_step(darray, dim)
        window_length = int(np.rint(window_length / delta))
        if window_length % 2 == 0:  # must be odd
            window_length += 1
    ret = scipy.signal.savgol_filter(np.asarray(darray), window_length,
                                     polyorder, deriv, delta, axis, mode, cval)
    return darray.__array_wrap__(ret)
