import { createRouter, createWebHistory } from "vue-router";

const routes = [
  {
    path: "/",
    name: "upload",
    component: () => import("./views/UploadView.vue"),
  },
  {
    path: "/tasks",
    name: "tasks",
    component: () => import("./views/TaskListView.vue"),
  },
  {
    path: "/rules",
    name: "rules",
    component: () => import("./views/RulesView.vue"),
  },
  {
    path: "/agent",
    name: "agent",
    component: () => import("./views/AgentView.vue"),
  },
  {
    path: "/reports",
    name: "reports",
    component: () => import("./views/ReportView.vue"),
  },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

export default router;
