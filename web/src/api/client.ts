import axios from 'axios'
import { ElMessage } from 'element-plus'

const http = axios.create({
  baseURL: '/api',
  timeout: 60_000,
})

http.interceptors.response.use(
  resp => {
    const body = resp.data
    // All API responses are { data, error } envelopes.
    if (body && typeof body === 'object' && 'data' in body && 'error' in body) {
      if (body.error) {
        ElMessage.error(body.error.message || body.error.code)
        return Promise.reject(body.error)
      }
      return { ...resp, data: body.data }
    }
    return resp
  },
  err => {
    const detail = err.response?.data?.detail
    const message = detail?.error?.message || detail?.message || err.message
    ElMessage.error(message)
    return Promise.reject(err)
  },
)

export default http
