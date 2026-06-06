import axios from 'axios'

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 30000,
})

// ── 小说管理 ──

/** 列出所有小说 */
export function fetchNovels() {
  return api.get('/novels').then(r => r.data.novels)
}

/** 获取小说详情 */
export function fetchNovelDetail(name) {
  return api.get(`/novels/${name}`).then(r => r.data)
}

/** 上传小说文件 */
export function uploadNovelFiles(novelName, files) {
  const formData = new FormData()
  formData.append('novel_name', novelName)
  for (const file of files) {
    formData.append('files', file)
  }
  // 对齐后端: POST /upload
  return api.post('/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  }).then(r => r.data)
}

/** 删除小说 */
export function deleteNovel(name) {
  return api.delete(`/novels/${name}`).then(r => r.data)
}

// ── 转换任务 ──

/** 发起转换（对齐后端: POST /convert/{novel_name}） */
export function startConvert(novelName, options = {}) {
  const params = {}
  if (options.chapters) {
    params.chapters = options.chapters
  }
  // 对齐后端: POST /convert/{novel_name}
  return api.post(`/convert/${novelName}`, null, { params }).then(r => r.data)
}

/** 查询任务状态（对齐后端: GET /convert/{task_id}/status） */
export function fetchTaskStatus(taskId) {
  return api.get(`/convert/${taskId}/status`).then(r => r.data)
}

// ── 输出结果 ──

/** 预览 YAML 内容（对齐后端: GET /preview/{name}） */
export function fetchYamlPreview(name) {
  return api.get(`/preview/${name}`).then(r => r.data.yaml)
}

/** 下载 YAML 文件（对齐后端: GET /download/{name}） */
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
