import axios from 'axios'

const API_BASE = 'http://localhost:8000/api'

const apiClient = axios.create({
  baseURL: API_BASE,
  timeout: 60000,
})

export async function uploadPdf(file) {
  const formData = new FormData()
  formData.append('file', file)
  const response = await apiClient.post('/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return response.data
}

export async function askQuestion(question, history = [], docIds = null) {
  const response = await apiClient.post('/chat', {
    question,
    history,
    doc_ids: docIds && docIds.length > 0 ? docIds : null,
    min_score: 0.25,
  })
  return response.data
}

export async function checkHealth() {
  const response = await axios.get('http://localhost:8000/health')
  return response.data
}
