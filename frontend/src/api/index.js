import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 600000,  // 10 分钟（转换可能很慢）
})

/** 上传小说文件 */
export function uploadNovelFiles(novelName, files) {
  const formData = new FormData()
  formData.append('novel_name', novelName)
  for (const file of files) {
    formData.append('files', file)
  }
  return api.post('/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  }).then(r => r.data)
}

/** 发起转换 */
export function startConvert(novelName) {
  return api.post('/convert', { novel_name: novelName }).then(r => r.data)
}

/** 查询任务状态 */
export function fetchTaskStatus(taskId) {
  return api.get(`/status/${taskId}`).then(r => r.data)
}

/** 预览 YAML 内容（返回文本） */
export function previewYaml(name) {
  return api.get(`/preview/${name}`).then(r => r.data)
}

/** 下载 YAML 文件 */
export function downloadYaml(name) {
  return api.get(`/download/${name}`, {
    responseType: 'blob',
  }).then(r => {
    const url = URL.createObjectURL(r.data)
    const a = document.createElement('a')
    a.href = url
    a.download = `${name}_script.yaml`
    a.click()
    URL.revokeObjectURL(url)
  })
}

export default api
