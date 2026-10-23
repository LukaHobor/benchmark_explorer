"""OLS/GLM with inference, HAC SEs, LOO-CV, bootstrap, nonlinear fits.
statsmodels is not in this environment; everything here is computed directly."""
import numpy as np
from scipy import stats, optimize
from scipy.special import gammaln


class OLS:
    def __init__(self, X, y, names=None):
        X = np.asarray(X, float); y = np.asarray(y, float)
        if X.ndim == 1: X = X[:, None]
        self.X, self.y = X, y
        self.n, self.k = X.shape
        self.df = self.n - self.k
        self.XtXi = np.linalg.pinv(X.T @ X)
        self.beta = self.XtXi @ X.T @ y
        self.fitted = X @ self.beta
        self.resid = y - self.fitted
        self.ssr = float(self.resid @ self.resid)
        self.sigma2 = self.ssr / self.df
        self.cov = self.sigma2 * self.XtXi
        self.se = np.sqrt(np.diag(self.cov))
        self.t = self.beta / self.se
        self.p = 2 * stats.t.sf(np.abs(self.t), self.df)
        tc = stats.t.ppf(0.975, self.df)
        self.ci = np.c_[self.beta - tc*self.se, self.beta + tc*self.se]
        ybar = y.mean(); self.tss = float(((y - ybar)**2).sum())
        self.r2 = 1 - self.ssr/self.tss
        self.adj_r2 = 1 - (1-self.r2)*(self.n-1)/self.df
        q = self.k - 1
        self.fstat = ((self.tss - self.ssr)/q)/self.sigma2 if q > 0 else np.nan
        self.f_p = stats.f.sf(self.fstat, q, self.df) if q > 0 else np.nan
        self.llf = -0.5*self.n*(np.log(2*np.pi) + np.log(self.ssr/self.n) + 1)
        kk = self.k + 1
        self.aic = -2*self.llf + 2*kk
        self.aicc = self.aic + (2*kk*(kk+1))/max(self.n-kk-1, 1e-9)
        self.bic = -2*self.llf + np.log(self.n)*kk
        self.names = names or [f"x{i}" for i in range(self.k)]
        self.dw = float(np.sum(np.diff(self.resid)**2)/self.ssr)
        r = self.resid
        self.rho1 = float(np.corrcoef(r[:-1], r[1:])[0, 1]) if self.n > 3 else np.nan
        self.sigma = np.sqrt(self.sigma2)
        # HAC (Newey-West) covariance
        self.hac_cov = self._hac()
        self.hac_se = np.sqrt(np.diag(self.hac_cov))
        self.hac_t = self.beta / self.hac_se
        self.hac_p = 2*stats.t.sf(np.abs(self.hac_t), self.df)
        self.hac_ci = np.c_[self.beta - tc*self.hac_se, self.beta + tc*self.hac_se]
        # normality / heteroskedasticity
        self.sw = stats.shapiro(r) if 3 <= self.n <= 5000 else (np.nan, np.nan)
        self.bp = self._breusch_pagan()

    def _hac(self, L=None):
        n, X, u = self.n, self.X, self.resid
        if L is None: L = max(1, int(np.floor(4*(n/100)**(2/9))))
        S = (X * u[:, None]).T @ (X * u[:, None])
        for l in range(1, L+1):
            w = 1 - l/(L+1)
            Xu = X * u[:, None]
            G = Xu[l:].T @ Xu[:-l]
            S += w*(G + G.T)
        self.hac_lag = L
        return self.XtXi @ S @ self.XtXi * (n/max(self.df, 1))

    def _breusch_pagan(self):
        g = self.resid**2 / (self.ssr/self.n)
        aux = OLS_raw(self.X, g)
        lm = 0.5*(aux['tss'] - aux['ssr'])
        return lm, stats.chi2.sf(lm, self.k-1)

    def summary(self, label="", hac=False):
        L = [f"  {label}"] if label else []
        se, t, p, ci = ((self.hac_se, self.hac_t, self.hac_p, self.hac_ci) if hac
                        else (self.se, self.t, self.p, self.ci))
        L.append(f"  {'term':<16}{'coef':>11}{'std err':>10}{'t':>8}{'P>|t|':>11}   [95% CI]")
        for i, nm in enumerate(self.names):
            L.append(f"  {nm:<16}{self.beta[i]:>11.5f}{se[i]:>10.5f}{t[i]:>8.2f}"
                     f"{p[i]:>11.3g}   [{ci[i,0]:.5f}, {ci[i,1]:.5f}]")
        L.append(f"  n={self.n}  df={self.df}  R2={self.r2:.4f}  adjR2={self.adj_r2:.4f}  "
                 f"F={self.fstat:.1f} (p={self.f_p:.3g})  s={self.sigma:.4f}")
        L.append(f"  AIC={self.aic:.2f} AICc={self.aicc:.2f} BIC={self.bic:.2f}  "
                 f"DW={self.dw:.2f} rho1={self.rho1:+.3f}  Shapiro W={self.sw[0]:.3f} (p={self.sw[1]:.2f})"
                 f"  BP p={self.bp[1]:.2f}")
        return "\n".join(L)

    def predict(self, Xn):
        Xn = np.atleast_2d(np.asarray(Xn, float)); return Xn @ self.beta

    def conf_interval(self, Xn, alpha=.05):
        Xn = np.atleast_2d(np.asarray(Xn, float)); yh = Xn @ self.beta
        v = np.array([x @ self.cov @ x for x in Xn])
        t = stats.t.ppf(1-alpha/2, self.df)
        return yh, yh - t*np.sqrt(v), yh + t*np.sqrt(v)

    def pred_interval(self, Xn, alpha=.05):
        Xn = np.atleast_2d(np.asarray(Xn, float)); yh = Xn @ self.beta
        v = np.array([self.sigma2 + x @ self.cov @ x for x in Xn])
        t = stats.t.ppf(1-alpha/2, self.df)
        return yh, yh - t*np.sqrt(v), yh + t*np.sqrt(v)


def OLS_raw(X, y):
    X = np.atleast_2d(np.asarray(X, float)); y = np.asarray(y, float)
    b = np.linalg.pinv(X.T @ X) @ X.T @ y
    r = y - X @ b
    return dict(beta=b, ssr=float(r @ r), tss=float(((y-y.mean())**2).sum()))


def loo_cv(X, y):
    """Leave-one-out CV in the model's own (log) space and in count space."""
    X = np.atleast_2d(np.asarray(X, float)); y = np.asarray(y, float)
    n = len(y); e_log = np.zeros(n); e_cnt = np.zeros(n)
    for i in range(n):
        m = np.ones(n, bool); m[i] = False
        b = np.linalg.pinv(X[m].T @ X[m]) @ X[m].T @ y[m]
        yh = X[i] @ b
        e_log[i] = y[i] - yh
        e_cnt[i] = np.exp(y[i]) - np.exp(yh)
    return dict(rmse_log=float(np.sqrt((e_log**2).mean())),
                mae_log=float(np.abs(e_log).mean()),
                rmse_cnt=float(np.sqrt((e_cnt**2).mean())),
                mape=float(np.mean(np.abs(e_cnt)/np.exp(y))))


def boot_slope(x, y, B=20000, seed=7):
    """Wild (Rademacher) bootstrap CI for the slope of y = a + b x."""
    rng = np.random.default_rng(seed)
    X = np.c_[np.ones(len(x)), x]
    b = np.linalg.pinv(X.T @ X) @ X.T @ y
    fit = X @ b; res = y - fit
    out = np.empty(B)
    for i in range(B):
        ys = fit + res*rng.choice([-1.0, 1.0], len(y))
        out[i] = (np.linalg.pinv(X.T @ X) @ X.T @ ys)[1]
    return float(np.percentile(out, 2.5)), float(np.percentile(out, 97.5)), out


def glm(X, y, family='poisson', names=None, maxiter=200, tol=1e-11):
    """Log-link Poisson (quasi-scaled) or NB2 GLM by IRLS."""
    X = np.atleast_2d(np.asarray(X, float)); y = np.asarray(y, float)
    n, k = X.shape
    beta = np.zeros(k); beta[0] = np.log(max(y.mean(), 1e-6))
    alpha = 0.0
    for _ in range(6):
        for _ in range(maxiter):
            mu = np.exp(np.clip(X @ beta, -50, 50))
            W = mu/(1 + alpha*mu) if family == 'nb2' else mu
            z = X @ beta + (y - mu)/np.maximum(mu, 1e-12)
            XtW = X.T*W
            nb = np.linalg.pinv(XtW @ X) @ (XtW @ z)
            if np.max(np.abs(nb - beta)) < tol: beta = nb; break
            beta = nb
        if family != 'nb2': break
        mu = np.exp(np.clip(X @ beta, -50, 50))
        f = lambda a: -float(np.sum(gammaln(y + 1/a) - gammaln(1/a) - gammaln(y+1)
                     + (1/a)*np.log(1/(1+a*mu)) + y*np.log(a*mu/(1+a*mu))))
        r = optimize.minimize_scalar(f, bounds=(1e-6, 20), method='bounded')
        if abs(r.x - alpha) < 1e-8: alpha = r.x; break
        alpha = r.x
    mu = np.exp(np.clip(X @ beta, -50, 50))
    W = mu/(1 + alpha*mu) if family == 'nb2' else mu
    cov = np.linalg.pinv((X.T*W) @ X)
    se = np.sqrt(np.diag(cov))
    pearson = float(np.sum((y - mu)**2/np.maximum(mu, 1e-12)))
    disp = float(np.sum((y-mu)**2/np.maximum(mu, 1e-12)))/(n-k)
    if family == 'quasipoisson':
        se = se*np.sqrt(max(disp, 1.0))
    z = beta/se; p = 2*stats.norm.sf(np.abs(z))
    if family == 'nb2':
        llf = float(np.sum(gammaln(y + 1/alpha) - gammaln(1/alpha) - gammaln(y+1)
              + (1/alpha)*np.log(1/(1+alpha*mu)) + y*np.log(np.maximum(alpha*mu, 1e-300)/(1+alpha*mu))))
        kk = k + 1
    else:
        llf = float(np.sum(y*np.log(np.maximum(mu, 1e-12)) - mu - gammaln(y+1))); kk = k
    return dict(beta=beta, se=se, z=z, p=p, disp=disp, mu=mu, alpha=alpha,
                ci=np.c_[beta-1.96*se, beta+1.96*se], llf=llf,
                aic=-2*llf+2*kk, bic=-2*llf+np.log(n)*kk,
                names=names or [f"x{i}" for i in range(k)])


def chow(x, y, split):
    """Chow structural-break F-test at index `split` (first obs of segment 2)."""
    X = np.c_[np.ones(len(x)), x]
    r = OLS(X, y); ssr_p = r.ssr
    a, b = OLS(X[:split], y[:split]), OLS(X[split:], y[split:])
    ssr_u = a.ssr + b.ssr
    k = 2; dfu = len(y) - 2*k
    F = ((ssr_p - ssr_u)/k)/(ssr_u/dfu)
    return F, stats.f.sf(F, k, dfu), dfu


def fit_nonlinear(f, p0, x, y, bounds=None):
    try:
        popt, _ = optimize.curve_fit(f, x, y, p0=p0, maxfev=200000,
                                     bounds=bounds or (-np.inf, np.inf))
    except Exception:
        return None
    yh = f(x, *popt); res = y - yh
    n, k = len(y), len(popt)
    ssr = float(res @ res); tss = float(((y-y.mean())**2).sum())
    llf = -0.5*n*(np.log(2*np.pi)+np.log(ssr/n)+1); kk = k+1
    return dict(p=popt, ssr=ssr, r2=1-ssr/tss, llf=llf, aic=-2*llf+2*kk,
                aicc=-2*llf+2*kk+(2*kk*(kk+1))/max(n-kk-1, 1e-9),
                bic=-2*llf+np.log(n)*kk, fitted=yh)
