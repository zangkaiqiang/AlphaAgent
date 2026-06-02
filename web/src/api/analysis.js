import http from './client';
// ----------------------------------------------------------------------
export const analysisApi = {
    companyOverview: (symbol, days = 250) => http.get(`/analysis/company/${symbol}`, { params: { days } })
        .then(r => r.data),
    companyKline: (symbol, days = 180, freq = '1d') => http.get(`/analysis/company/${symbol}/kline`, { params: { days, freq } })
        .then(r => r.data),
    industryList: (sort = 'change', descending = true) => http.get('/analysis/industry', { params: { sort, descending } })
        .then(r => r.data),
    industryDetail: (code) => http.get(`/analysis/industry/${code}`).then(r => r.data),
    marketSnapshot: () => http.get('/analysis/market/snapshot').then(r => r.data),
};
//# sourceMappingURL=analysis.js.map