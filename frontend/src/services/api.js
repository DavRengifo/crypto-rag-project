const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

export const getPrices = async () => {
    const response = await fetch(`${API_URL}/prices`)
    if (!response.ok) {
        throw new Error('Failed to fetch prices');
    }
    return response.json();
};

export const getPriceHistory = async (symbol, period = '24h') => {
    const response = await fetch(`${API_URL}/prices/${symbol}/history?period=${period}`)
    if (!response.ok) {
        throw new Error(`Failed to fetch price history for ${symbol}`);
    }
    return response.json();
};

export const getTopMovers = async () => {
    const response = await fetch(`${API_URL}/prices/top-movers`)
    if (!response.ok) {
        throw new Error('Failed to fetch top movers');
    }
    return response.json();
};

export const getStats = async () => {
    const response = await fetch(`${API_URL}/stats`)
    if (!response.ok) throw new Error('Failed to fetch stats')
    return response.json()
};

export const getNews = async (symbol = null) => {
    const url = symbol ? `${API_URL}/news?symbol=${symbol}` : `${API_URL}/news`
    const response = await fetch(url)
    if (!response.ok) {
        throw new Error('Failed to fetch news')
    }
    return response.json()
};

export const getMarketReport = async () => {
    const response = await fetch(`${API_URL}/reports/market/latest`)
    if (!response.ok) {
        throw new Error('Failed to fetch market report')
    }
    return response.json()
};

export const generateReport = async (symbols, period = '1y') => {
    const response = await fetch(`${API_URL}/reports/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ symbols, period })
    })
    if (!response.ok) {
        throw new Error('Failed to generate report')
    }
    return response.json()
};

export const askQuestion = async (question) => {
    const response = await fetch(`${API_URL}/ask`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question })
    });
    if (!response.ok) {
        throw new Error('Failed to ask question');
    }
    return response.json();
};
