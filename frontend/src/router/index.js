import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    name: 'home',
    component: () => import('../views/HomeView.vue'),
    meta: { title: '首页' },
  },
  {
    path: '/org/employee-validate',
    name: 'employee-validate',
    component: () => import('../views/EmployeeValidateView.vue'),
    meta: { title: '员工档案校验' },
  },
  {
    path: '/org/structure',
    name: 'org-structure',
    component: () => import('../views/OrgStructureView.vue'),
    meta: { title: '组织架构解析' },
  },
  {
    path: '/payroll/calculate',
    name: 'payroll-calculate',
    component: () => import('../views/PayrollCalcView.vue'),
    meta: { title: '工资计算器' },
  },
  {
    path: '/payroll/batch',
    name: 'payroll-batch',
    component: () => import('../views/PayrollBatchView.vue'),
    meta: { title: '批量算薪' },
  },
]

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes,
})

export default router