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

export const getCryptoNews = async (symbol) => {
    const response = await fetch(`${API_URL}/news/${symbol}`)
    if (!response.ok) {
        throw new Error(`Failed to fetch news for ${symbol}`);
    }
    return response.json();
};

export const getNews = async () => {
    const response = await fetch(`${API_URL}/news`)
    if (!response.ok) {
        throw new Error('Failed to fetch news');
    }
    return response.json();
};

export const getSummary = async (symbol, options = {}) => {
    const params = new URLSearchParams()
    if (options.includeNews) params.append('include_news', 'true')
    if (options.includeSentiment) params.append('include_sentiment', 'true')
    
    const url = `${API_URL}/summary/${symbol}?${params}`
    const response = await fetch(url)
    if (!response.ok) throw new Error(`Failed to fetch summary for ${symbol}`)
    return response.json()
}

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
