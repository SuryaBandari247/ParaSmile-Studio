import axios from 'axios'

const client = axios.create({
  baseURL: '/api',
  headers: { 'Content-Type': 'application/json' },
})

client.interceptors.response.use(
  (response) => response,
  (error) => {
    const detail = error.response?.data?.detail
    if (detail && typeof detail === 'object' && detail.message) {
      return Promise.reject(new Error(detail.message))
    }
    return Promise.reject(error)
  }
)

export default client
