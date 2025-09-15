"use client";

import React, { useState } from "react";
// @ts-ignore
import { Search, Plus, MoreHorizontal, Calendar, User } from "lucide-react";

type Task = { id: number; title: string; status: "pending" | "active" | "done"; category: string; dueDate: string };

export default function Home(): JSX.Element {
  const [currentView, setCurrentView] = useState<string>("tasks");
  const [tasks, setTasks] = useState<Task[]>([
    { id: 1, title: "プレゼン資料作成", status: "active", category: "work", dueDate: "9/16" },
    { id: 2, title: "英語の宿題", status: "pending", category: "study", dueDate: "9/17" },
    { id: 3, title: "部屋の掃除", status: "done", category: "personal", dueDate: "9/15" },
  ]);

  const [newTask, setNewTask] = useState<string>("");
  const [selectedFilter, setSelectedFilter] = useState<string>("all");
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [showAddForm, setShowAddForm] = useState<boolean>(false);
  const [motivation, setMotivation] = useState<number>(50);

  const addTask = () => {
    if (!newTask.trim()) return;
    const taskObj: Task = {
      id: Date.now(),
      title: newTask,
      status: "pending",
      category: "personal",
      dueDate: new Date().toLocaleDateString("ja-JP", { month: "numeric", day: "numeric" }),
    };
    setTasks((p) => [...p, taskObj]);
    setNewTask("");
    setShowAddForm(false);
  };

  const updateTaskStatus = (taskId: number, newStatus: Task["status"]) => setTasks((p) => p.map((t) => (t.id === taskId ? { ...t, status: newStatus } : t)));
  const deleteTask = (taskId: number) => setTasks((p) => p.filter((t) => t.id !== taskId));

  return (
    <div className="min-h-screen bg-white">
      <header className="border-b border-gray-200 bg-white sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center space-x-4">
              <h1 className="text-xl font-semibold text-gray-900">Sista</h1>
              <nav className="flex space-x-4">
                <button onClick={() => setCurrentView("tasks")} className={`text-sm font-medium ${currentView === "tasks" ? "text-gray-900 border-b-2 border-gray-900" : "text-gray-500 hover:text-gray-700"} pb-4`}>タスク</button>
                <button onClick={() => setCurrentView("calendar")} className={`text-sm font-medium ${currentView === "calendar" ? "text-gray-900 border-b-2 border-gray-900" : "text-gray-500 hover:text-gray-700"} pb-4`}>カレンダー</button>
                <button onClick={() => setCurrentView("chat")} className={`text-sm font-medium ${currentView === "chat" ? "text-gray-900 border-b-2 border-gray-900" : "text-gray-500 hover:text-gray-700"} pb-4`}>アシスタント</button>
              </nav>
            </div>
            <div className="flex items-center space-x-4">
              <User className="w-8 h-8 p-2 text-gray-400 bg-gray-100 rounded-full" />
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {currentView === "tasks" && (
          <div className="space-y-6">
            <div className="flex justify-between items-center">
              <div className="flex items-center space-x-4">
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
                  <input type="text" placeholder="タスクを検索..." value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)} className="pl-10 pr-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent w-64" />
                </div>
                <select value={selectedFilter} onChange={(e) => setSelectedFilter(e.target.value)} className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500">
                  <option value="all">すべて</option>
                  <option value="active">進行中</option>
                  <option value="pending">未着手</option>
                  <option value="done">完了</option>
                </select>
              </div>
              <button onClick={() => setShowAddForm((v) => !v)} className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-gray-900 hover:bg-gray-800 focus:outline-none focus:ring-2 focus:ring-gray-500">
                <Plus className="w-4 h-4 mr-2" />新規タスク
              </button>
            </div>

            {showAddForm && (
              <div className="bg-gray-50 p-4 rounded-lg border border-gray-200">
                <div className="flex space-x-3">
                  <input type="text" placeholder="タスクを入力..." value={newTask} onChange={(e) => setNewTask(e.target.value)} className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500" onKeyDown={(e) => e.key === "Enter" && addTask()} autoFocus />
                  <button onClick={addTask} className="px-4 py-2 bg-gray-900 text-white text-sm rounded-md hover:bg-gray-800">追加</button>
                  <button onClick={() => { setShowAddForm(false); setNewTask(""); }} className="px-4 py-2 border border-gray-300 text-gray-700 text-sm rounded-md hover:bg-gray-50">キャンセル</button>
                </div>
              </div>
            )}

            <div className="space-y-2">
              {tasks.filter((task) => {
                const matchesSearch = task.title.toLowerCase().includes(searchQuery.toLowerCase());
                const matchesFilter = selectedFilter === "all" || task.status === selectedFilter;
                return matchesSearch && matchesFilter;
              }).map((task) => (
                <div key={task.id} className={`bg-white border border-gray-200 hover:border-gray-300 transition-colors border-l-4 ${task.category === "work" ? "border-l-red-500" : task.category === "study" ? "border-l-blue-500" : task.category === "personal" ? "border-l-purple-500" : task.category === "health" ? "border-l-green-500" : "border-l-gray-300"}`}>
                  <div className="px-4 py-3">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center space-x-3 flex-1">
                        <input type="checkbox" checked={task.status === "done"} onChange={(e) => updateTaskStatus(task.id, e.target.checked ? "done" : "pending")} className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500" />
                        <div className="flex-1">
                          <h3 className={`text-sm font-medium ${task.status === "done" ? "line-through text-gray-500" : "text-gray-900"}`}>{task.title}</h3>
                          <div className="flex items-center space-x-2 mt-1">
                            <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${task.status === "done" ? "bg-green-100 text-green-800" : task.status === "active" ? "bg-blue-100 text-blue-800" : "bg-gray-100 text-gray-600"}`}>{task.status === "done" ? "完了" : task.status === "active" ? "進行中" : "未着手"}</span>
                            <span className="text-xs text-gray-500">{task.dueDate}</span>
                          </div>
                        </div>
                      </div>
                      <div className="flex items-center space-x-2">
                        {task.status !== "done" && <button onClick={() => updateTaskStatus(task.id, task.status === "active" ? "pending" : "active")} className="text-xs px-2 py-1 text-blue-600 hover:bg-blue-50 rounded">{task.status === "active" ? "一時停止" : "開始"}</button>}
                        <button onClick={() => deleteTask(task.id)} className="text-gray-400 hover:text-red-500 p-1"><MoreHorizontal className="w-4 h-4" /></button>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>

            <div className="mt-8 flex items-center gap-6">
              <span className="text-lg text-gray-700">やる気ゲージ</span>
              <div className="flex-1 h-6 bg-gray-200 rounded-full overflow-hidden">
                <div style={{ width: `${motivation}%` }} className="h-6 bg-gradient-to-r from-pink-400 to-cyan-400 transition-all"></div>
              </div>
              <span className="text-cyan-500 font-bold ml-2">{motivation}</span>
              {motivation < 30 && <span className="text-pink-500 font-bold ml-4">妹「やる気ないなら、強制実行しちゃうよ？」</span>}
            </div>
          </div>
        )}

        {currentView === "calendar" && (
          <div className="text-center py-12">
            <Calendar className="w-12 h-12 text-gray-400 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">カレンダー機能</h3>
            <p className="text-gray-500">カレンダービューは開発中です</p>
          </div>
        )}

        {currentView === "chat" && (
          <div className="max-w-2xl mx-auto">
            <div className="bg-white border border-gray-200 rounded-lg">
              <div className="p-4 border-b border-gray-200">
                <h2 className="text-lg font-medium text-gray-900">Sistaアシスタント</h2>
                <p className="text-sm text-gray-500">タスク管理をサポートします</p>
              </div>
              <div className="p-6 h-96 overflow-y-auto space-y-4">
                <div className="text-sm text-gray-500">アシスタントに話しかけてください</div>
              </div>
              <div className="p-4 border-t border-gray-200">
                <div className="flex space-x-3">
                  <input type="text" placeholder="メッセージを入力..." value={""} onChange={() => { }} className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm" />
                  <button className="px-4 py-2 bg-gray-900 text-white text-sm rounded-md hover:bg-gray-800">送信</button>
                </div>
              </div>
            </div>
          </div>
        )}

      </main>
    </div>
  );
}
