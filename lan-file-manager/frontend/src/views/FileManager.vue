<template>
  <div class="file-manager">
    <!-- 顶部工具栏 -->
    <div class="toolbar">
      <div class="toolbar-left">
        <el-button @click="goBack" :disabled="currentPath === ''">
          <el-icon><ArrowLeft /></el-icon> 返回
        </el-button>
        <el-breadcrumb separator="/">
          <el-breadcrumb-item @click="navigateTo('')">根目录</el-breadcrumb-item>
          <el-breadcrumb-item
            v-for="(part, index) in pathParts"
            :key="index"
            @click="navigateTo(pathParts.slice(0, index + 1).join('/'))"
          >
            {{ part }}
          </el-breadcrumb-item>
        </el-breadcrumb>
      </div>
      
      <div class="toolbar-right">
        <el-button type="primary" @click="showUploadDialog">
          <el-icon><Upload /></el-icon> 上传文件
        </el-button>
        <el-button @click="showCreateFolderDialog">
          <el-icon><FolderAdd /></el-icon> 新建文件夹
        </el-button>
        <el-button @click="refresh">
          <el-icon><Refresh /></el-icon> 刷新
        </el-button>
        <el-button type="danger" @click="logout">
          <el-icon><SwitchButton /></el-icon> 退出
        </el-button>
      </div>
    </div>
    
    <!-- 文件列表 -->
    <el-table
      :data="files"
      v-loading="loading"
      @row-click="handleRowClick"
      highlight-current-row
    >
      <el-table-column width="50">
        <template #default="{ row }">
          <el-icon :size="20" v-if="row.is_dir"><Folder /></el-icon>
          <el-icon :size="20" v-else><Document /></el-icon>
        </template>
      </el-table-column>
      
      <el-table-column prop="name" label="文件名" min-width="200">
        <template #default="{ row }">
          <span class="file-name" :class="{ 'is-dir': row.is_dir }">{{ row.name }}</span>
        </template>
      </el-table-column>
      
      <el-table-column prop="size" label="大小" width="120">
        <template #default="{ row }">
          {{ row.is_dir ? '-' : formatSize(row.size) }}
        </template>
      </el-table-column>
      
      <el-table-column prop="permissions" label="权限" width="100" />
      
      <el-table-column label="操作" width="200" fixed="right">
        <template #default="{ row }">
          <el-button-group>
            <el-button
              v-if="!row.is_dir"
              size="small"
              @click.stop="downloadFile(row)"
            >
              <el-icon><Download /></el-icon>
            </el-button>
            <el-button
              v-if="row.is_dir"
              size="small"
              type="primary"
              @click.stop="downloadFolder(row)"
              title="下载文件夹"
            >
              <el-icon><Download /></el-icon>
            </el-button>
            <el-button
              size="small"
              @click.stop="renameFile(row)"
            >
              <el-icon><Edit /></el-icon>
            </el-button>
            <el-button
              size="small"
              type="danger"
              @click.stop="deleteFile(row)"
            >
              <el-icon><Delete /></el-icon>
            </el-button>
          </el-button-group>
        </template>
      </el-table-column>
    </el-table>
    
    <!-- 空状态 -->
    <el-empty v-if="!loading && files.length === 0" description="暂无文件" />
    
    <!-- 上传对话框 -->
    <el-dialog
      v-model="uploadDialogVisible"
      title="上传文件"
      width="500px"
    >
      <el-upload
        ref="uploadRef"
        drag
        action="/api/files/upload"
        :data="{ path: currentPath }"
        :headers="uploadHeaders"
        :on-success="handleUploadSuccess"
        :on-error="handleUploadError"
        :before-upload="beforeUpload"
        multiple
      >
        <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
        <div class="el-upload__text">
          拖拽文件到此处或 <em>点击上传</em>
        </div>
      </el-upload>
      
      <template #footer>
        <el-button @click="uploadDialogVisible = false">关闭</el-button>
      </template>
    </el-dialog>
    
    <!-- 新建文件夹对话框 -->
    <el-dialog
      v-model="createFolderDialogVisible"
      title="新建文件夹"
      width="400px"
    >
      <el-input
        v-model="newFolderName"
        placeholder="请输入文件夹名称"
        @keyup.enter="createFolder"
      />
      <template #footer>
        <el-button @click="createFolderDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="createFolder" :loading="creating">确定</el-button>
      </template>
    </el-dialog>
    
    <!-- 重命名对话框 -->
    <el-dialog
      v-model="renameDialogVisible"
      title="重命名"
      width="400px"
    >
      <el-input
        v-model="newName"
        placeholder="请输入新名称"
        @keyup.enter="confirmRename"
      />
      <template #footer>
        <el-button @click="renameDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="confirmRename" :loading="renaming">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import api, { downloadApi } from '../api'

const router = useRouter()

// 状态
const files = ref([])
const loading = ref(false)
const currentPath = ref('')
const uploadDialogVisible = ref(false)
const createFolderDialogVisible = ref(false)
const renameDialogVisible = ref(false)
const newFolderName = ref('')
const newName = ref('')
const currentFile = ref(null)
const creating = ref(false)
const renaming = ref(false)
const uploadRef = ref()

// 计算属性
const pathParts = computed(() => {
  return currentPath.value ? currentPath.value.split('/').filter(Boolean) : []
})

const uploadHeaders = computed(() => ({
  Authorization: `Bearer ${localStorage.getItem('token')}`
}))

// 方法
const loadFiles = async () => {
  loading.value = true
  try {
    const res = await api.get('/files', { params: { path: currentPath.value } })
    files.value = res.data
  } catch (error) {
    console.error('加载文件列表失败:', error)
    console.error('错误详情:', error.response?.data)
    ElMessage.error('加载文件列表失败: ' + (error.response?.data?.detail || error.message))
  } finally {
    loading.value = false
  }
}

const goBack = () => {
  if (!currentPath.value) return
  const parts = currentPath.value.split('/').filter(Boolean)
  parts.pop()
  currentPath.value = parts.join('/')
  loadFiles()
}

const navigateTo = (path) => {
  currentPath.value = path
  loadFiles()
}

const handleRowClick = (row) => {
  if (row.is_dir) {
    currentPath.value = row.path
    loadFiles()
  }
}

const formatSize = (bytes) => {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

const showUploadDialog = () => {
  uploadDialogVisible.value = true
}

const beforeUpload = (file) => {
  // 大文件使用分片上传
  const MAX_SIZE = 100 * 1024 * 1024 // 100MB
  if (file.size > MAX_SIZE) {
    ElMessage.info('大文件将使用分片上传')
    // 这里可以实现分片上传逻辑
  }
  return true
}

const handleUploadSuccess = () => {
  ElMessage.success('上传成功')
  loadFiles()
}

const handleUploadError = (error) => {
  ElMessage.error('上传失败: ' + (error.response?.data?.detail || '未知错误'))
}

const showCreateFolderDialog = () => {
  newFolderName.value = ''
  createFolderDialogVisible.value = true
}

const createFolder = async () => {
  if (!newFolderName.value.trim()) {
    ElMessage.warning('请输入文件夹名称')
    return
  }
  
  creating.value = true
  try {
    const path = currentPath.value
      ? `${currentPath.value}/${newFolderName.value}`
      : newFolderName.value
    await api.post('/files/mkdir', null, { params: { path } })
    ElMessage.success('创建成功')
    createFolderDialogVisible.value = false
    loadFiles()
  } catch (error) {
    ElMessage.error('创建失败')
  } finally {
    creating.value = false
  }
}

const downloadFile = async (row) => {
  try {
    const res = await downloadApi.get('/files/download', {
      params: { path: row.path },
      responseType: 'blob'
    })
    
    const url = window.URL.createObjectURL(new Blob([res.data]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', row.name)
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)
  } catch (error) {
    ElMessage.error('下载失败')
  }
}

const downloadFolder = async (row) => {
  try {
    ElMessage.info('正在打包文件夹，请稍候...')
    
    const res = await downloadApi.get('/files/download-folder', {
      params: { path: row.path },
      responseType: 'blob'
    })
    
    const url = window.URL.createObjectURL(new Blob([res.data]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', `${row.name}.zip`)
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)
    
    ElMessage.success('文件夹下载完成')
  } catch (error) {
    console.error('下载文件夹失败:', error)
    ElMessage.error('下载文件夹失败: ' + (error.response?.data?.detail || '未知错误'))
  }
}

const renameFile = (row) => {
  currentFile.value = row
  newName.value = row.name
  renameDialogVisible.value = true
}

const confirmRename = async () => {
  if (!newName.value.trim() || newName.value === currentFile.value.name) {
    renameDialogVisible.value = false
    return
  }
  
  renaming.value = true
  try {
    const dir = currentPath.value
    const oldPath = currentFile.value.path
    const newPath = dir ? `${dir}/${newName.value}` : newName.value
    
    await api.post('/files/rename', null, {
      params: { old_path: oldPath, new_path: newPath }
    })
    ElMessage.success('重命名成功')
    renameDialogVisible.value = false
    loadFiles()
  } catch (error) {
    ElMessage.error('重命名失败')
  } finally {
    renaming.value = false
  }
}

const deleteFile = async (row) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除 "${row.name}" 吗？`,
      '确认删除',
      { type: 'warning' }
    )
    
    await api.delete('/files', {
      params: { path: row.path, is_dir: row.is_dir }
    })
    ElMessage.success('删除成功')
    loadFiles()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

const refresh = () => {
  loadFiles()
}

const logout = () => {
  localStorage.removeItem('token')
  router.push('/login')
}

onMounted(() => {
  loadFiles()
})
</script>

<style scoped>
.file-manager {
  padding: 20px;
  height: 100vh;
  display: flex;
  flex-direction: column;
}

.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  padding: 15px;
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
}

.toolbar-left {
  display: flex;
  align-items: center;
  gap: 15px;
}

.toolbar-right {
  display: flex;
  gap: 10px;
}

.el-breadcrumb {
  font-size: 14px;
}

.el-breadcrumb__item {
  cursor: pointer;
}

.el-breadcrumb__item:hover {
  color: #409eff;
}

.file-name {
  cursor: pointer;
}

.file-name.is-dir {
  color: #409eff;
  font-weight: 500;
}

.file-name:hover {
  text-decoration: underline;
}

.el-table {
  flex: 1;
  background: #fff;
  border-radius: 8px;
  overflow: hidden;
}
</style>
