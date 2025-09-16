/* Replace entire file with a single clean Client Component */
"use client";

import React, { useState } from "react";
import { Search, Plus, MoreHorizontal, Calendar, User } from "lucide-react";

type Task = {
  id: number;
  title: string;
  status: "pending" | "active" | "done";
  category: string;
  dueDate: string;
};

// 小さめのユーティリティ: ステータス/カテゴリに応じた Tailwind クラスを返す
const getStatusBadge = (status: Task["status"]) => {
  switch (status) {
    case "done":
      return "bg-green-100 text-green-800";
    case "active":
      return "bg-blue-100 text-blue-800";
    case "pending":
    default:
      return "bg-gray-100 text-gray-600";
  }
};

const getCategoryBorder = (category: string) => {
  switch (category) {
    case "work":
      return "border-l-red-500";
    case "study":
      return "border-l-blue-500";
    case "personal":
      return "border-l-purple-500";
    case "health":
      return "border-l-green-500";
    default:
      return "border-l-gray-300";
  }
};

export default function Home(): React.ReactElement {
  const [currentView, setCurrentView] = useState<string>("tasks");
  const [tasks, setTasks] = useState<Task[]>([]);

  const [userToken, setUserToken] = useState<string | null>(typeof window !== 'undefined' ? localStorage.getItem('sista_token') : null);
  const [username, setUsername] = useState<string | null>(typeof window !== 'undefined' ? localStorage.getItem('sista_user') : null);
  const [showAuthModal, setShowAuthModal] = useState(false);
  const [authMode, setAuthMode] = useState<'login'|'register'>('login');
  const [authName, setAuthName] = useState('');
  const [authPass, setAuthPass] = useState('');

  const [newTask, setNewTask] = useState<string>("");
  const [selectedFilter, setSelectedFilter] = useState<string>("all");
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [showAddForm, setShowAddForm] = useState<boolean>(false);
  const [motivation, setMotivation] = useState<number>(50);

  const addTask = () => {
    if (!newTask.trim()) return;
    const payload = {
      title: newTask,
      status: "pending",
      category: "personal",
      due_date: new Date().toLocaleDateString("ja-JP", { month: "numeric", day: "numeric" }),
    };
    const headers: any = { "Content-Type": "application/json" };
    if (userToken) headers['Authorization'] = `Bearer ${userToken}`;
    fetch("http://localhost:8000/tasks", {
      method: "POST",
      headers,
      body: JSON.stringify({ ...payload, user_id: undefined }),
    })
      .then((r) => r.json())
      .then((created) => {
        setTasks((p) => [...p, { id: created.id, title: created.title, status: created.status as Task['status'], category: created.category || 'personal', dueDate: created.due_date || '' }]);
        setNewTask("");
        setShowAddForm(false);
      })
      .catch(console.error);
  };

  const updateTaskStatus = (taskId: number, newStatus: Task["status"]) => {
    const headers: any = { "Content-Type": "application/json" };
    if (userToken) headers['Authorization'] = `Bearer ${userToken}`;
    fetch(`http://localhost:8000/tasks/${taskId}`, {
      method: "PUT",
      headers,
      body: JSON.stringify({ title: tasks.find(t => t.id === taskId)?.title || '', status: newStatus, category: tasks.find(t => t.id === taskId)?.category, user_id: undefined }),
    })
      .then((r) => r.json())
      .then((updated) => setTasks((p) => p.map((t) => (t.id === taskId ? { ...t, status: updated.status as Task['status'] } : t))))
      .catch(console.error);
  };

  const deleteTask = (taskId: number) => {
  const headers: any = {};
  if (userToken) headers['Authorization'] = `Bearer ${userToken}`;
  fetch(`http://localhost:8000/tasks/${taskId}`, { method: "DELETE", headers })
      .then(() => setTasks((p) => p.filter((t) => t.id !== taskId)))
      .catch(console.error);
  };

  // load tasks
  React.useEffect(() => {
    const headers: any = {};
    if (userToken) headers['Authorization'] = `Bearer ${userToken}`;
    fetch("http://localhost:8000/tasks", { headers })
      .then((r) => r.json())
      .then((data) => {
        setTasks(data.map((d: any) => ({ id: d.id, title: d.title, status: d.status, category: d.category || 'personal', dueDate: d.due_date || '' })));
      })
      .catch(console.error);
  }, []);

  // auth actions
  const doAuth = () => {
    const url = authMode === 'login' ? '/auth/login' : '/auth/register';
    fetch(`http://localhost:8000${url}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username: authName, password: authPass }),
    })
      .then(r => r.json())
      .then((data) => {
        if (data.access_token) {
          localStorage.setItem('sista_token', data.access_token);
          localStorage.setItem('sista_user', authName);
          setUserToken(data.access_token);
          setUsername(authName);
          setShowAuthModal(false);
          // refresh tasks for this user
          const headers: any = {};
          if (data.access_token) headers['Authorization'] = `Bearer ${data.access_token}`;
          fetch("http://localhost:8000/tasks", { headers }).then(r => r.json()).then((d) => setTasks(d.map((t:any) => ({ id: t.id, title: t.title, status: t.status, category: t.category || 'personal', dueDate: t.due_date || '' })))).catch(console.error);
        }
      })
      .catch(console.error);
  };

  const logout = () => {
    localStorage.removeItem('sista_token');
    localStorage.removeItem('sista_user');
    setUserToken(null);
    setUsername(null);
  }

  return (
    <div className="min-h-screen bg-white">
      <header className="border-b border-gray-200 bg-white sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center space-x-4">
              <h1 className="text-2xl font-semibold text-gray-900">Sista</h1>
              <nav className="flex space-x-6" role="navigation" aria-label="メインメニュー">
                <button aria-pressed={currentView === "tasks"} onClick={() => setCurrentView("tasks")} className={`text-base font-medium ${currentView === "tasks" ? "text-gray-900 border-b-2 border-gray-900" : "text-gray-500 hover:text-gray-700"} pb-4`}>
                  タスク
                </button>
                <button aria-pressed={currentView === "calendar"} onClick={() => setCurrentView("calendar")} className={`text-base font-medium ${currentView === "calendar" ? "text-gray-900 border-b-2 border-gray-900" : "text-gray-500 hover:text-gray-700"} pb-4`}>
                  カレンダー
                </button>
                <button aria-pressed={currentView === "chat"} onClick={() => setCurrentView("chat")} className={`text-base font-medium ${currentView === "chat" ? "text-gray-900 border-b-2 border-gray-900" : "text-gray-500 hover:text-gray-700"} pb-4`}>
                  アシスタント
                </button>
              </nav>
            </div>
            <div className="flex items-center space-x-4">
              {username ? (
                <div className="flex items-center space-x-3">
                  <div className="text-sm text-gray-700">{username}</div>
                  <button onClick={logout} className="px-3 py-1 bg-red-50 text-red-600 rounded">ログアウト</button>
                </div>
              ) : (
                <button onClick={() => { setAuthMode('login'); setShowAuthModal(true); }} className="px-3 py-1 bg-gray-100 rounded">ログイン</button>
              )}
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {currentView === "tasks" && (
          <div className="space-y-6">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              <div className="flex items-center space-x-4 w-full sm:w-auto">
                <div className="relative w-full sm:w-64">
                  <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
                  <input
                    aria-label="タスク検索"
                    type="text"
                    placeholder="タスクを検索..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="pl-12 pr-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent w-full"
                  />
                </div>
                <select
                  aria-label="フィルター"
                  value={selectedFilter}
                  onChange={(e) => setSelectedFilter(e.target.value)}
                  className="px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="all">すべて</option>
                  <option value="active">進行中</option>
                  <option value="pending">未着手</option>
                  <option value="done">完了</option>
                </select>
              </div>
              <div className="flex-shrink-0">
                <button
                  onClick={() => setShowAddForm((v) => !v)}
                  className="inline-flex items-center px-5 py-3 border border-transparent text-base font-medium rounded-lg text-white bg-gray-900 hover:bg-gray-800 focus:outline-none focus:ring-2 focus:ring-gray-500"
                  aria-expanded={showAddForm}
                >
                  <Plus className="w-5 h-5 mr-3" />
                  新規タスク
                </button>
              </div>
            </div>

            {showAddForm && (
              <div className="bg-gray-50 p-4 rounded-xl border border-gray-200">
                <div className="flex flex-col sm:flex-row sm:items-center gap-3">
                  <input
                    aria-label="新しいタスク"
                    type="text"
                    placeholder="タスクを入力..."
                    value={newTask}
                    onChange={(e) => setNewTask(e.target.value)}
                    className="flex-1 px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                    onKeyDown={(e) => e.key === "Enter" && addTask()}
                    autoFocus
                  />
                  <div className="flex-shrink-0 flex items-center space-x-2">
                    <button onClick={addTask} className="px-5 py-3 bg-gray-900 text-white rounded-lg hover:bg-gray-800">追加</button>
                    <button onClick={() => { setShowAddForm(false); setNewTask(""); }} className="px-4 py-3 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50">キャンセル</button>
                  </div>
                </div>
              </div>
            )}

            <div className="space-y-3">
              {tasks
                .filter((task) => {
                  const matchesSearch = task.title.toLowerCase().includes(searchQuery.toLowerCase());
                  const matchesFilter = selectedFilter === "all" || task.status === selectedFilter;
                  return matchesSearch && matchesFilter;
                })
                .map((task) => (
                  <div
                    key={task.id}
                    className={`bg-white border border-gray-200 hover:border-gray-300 transition-colors rounded-lg ${getCategoryBorder(task.category)}`}
                  >
                    <div className="px-4 py-4">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center space-x-4 flex-1">
                          <input
                            aria-label={`完了 ${task.title}`}
                            type="checkbox"
                            checked={task.status === "done"}
                            onChange={(e) => updateTaskStatus(task.id, e.target.checked ? "done" : "pending")}
                            className="w-6 h-6 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                          />
                          <div className="flex-1 min-w-0">
                            <h3 className={`text-base font-medium truncate ${task.status === "done" ? "line-through text-gray-500" : "text-gray-900"}`}>{task.title}</h3>
                            <div className="flex items-center space-x-3 mt-2">
                              <span className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${getStatusBadge(task.status)}`}>
                                {task.status === "done" ? "完了" : task.status === "active" ? "進行中" : "未着手"}
                              </span>
                              <span className="text-sm text-gray-500">{task.dueDate}</span>
                            </div>
                          </div>
                        </div>
                        <div className="flex items-center space-x-3">
                          {task.status !== "done" && (
                            <button onClick={() => updateTaskStatus(task.id, task.status === "active" ? "pending" : "active")} className="text-sm px-3 py-2 text-blue-600 hover:bg-blue-50 rounded-lg">
                              {task.status === "active" ? "一時停止" : "開始"}
                            </button>
                          )}
                          <button onClick={() => deleteTask(task.id)} className="text-gray-400 hover:text-red-500 p-2 rounded-full" aria-label={`削除 ${task.title}`}>
                            <MoreHorizontal className="w-5 h-5" />
                          </button>
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
            </div>

            <div className="mt-8 flex flex-col sm:flex-row items-center gap-4">
              <span className="text-lg text-gray-700">やる気ゲージ</span>
              <div className="flex-1 h-8 bg-gray-200 rounded-full overflow-hidden">
                <div style={{ width: `${motivation}%` }} className="h-8 bg-gradient-to-r from-pink-400 to-cyan-400 transition-all" />
              </div>
              <span className="text-cyan-500 font-bold ml-2">{motivation}%</span>
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
                <div className="flex space-x-3">
                  <div className="w-10 h-10 bg-gray-200 rounded-full flex items-center justify-center">
                    <span className="text-sm font-medium text-gray-600">S</span>
                  </div>
                  <div className="flex-1">
                    <p className="text-sm text-gray-900">こんにちは！今日のタスクをチェックしましょう。</p>
                    <p className="text-xs text-gray-500 mt-1">2分前</p>
                  </div>
                </div>
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

      {/* auth modal */}
      {showAuthModal && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 w-full max-w-md">
            <h3 className="text-lg font-medium mb-4">{authMode === 'login' ? 'ログイン' : '新規登録'}</h3>
            <div className="space-y-3">
              <input className="w-full px-3 py-2 border rounded" placeholder="ユーザー名" value={authName} onChange={(e) => setAuthName(e.target.value)} />
              <input className="w-full px-3 py-2 border rounded" placeholder="パスワード" type="password" value={authPass} onChange={(e) => setAuthPass(e.target.value)} />
              <div className="flex justify-between items-center">
                <div>
                  <button onClick={() => { setAuthMode(authMode === 'login' ? 'register' : 'login'); }} className="text-sm text-blue-600">{authMode === 'login' ? 'アカウント作成' : 'ログイン画面へ'}</button>
                </div>
                <div className="flex space-x-2">
                  <button onClick={() => setShowAuthModal(false)} className="px-3 py-2 border rounded">キャンセル</button>
                  <button onClick={doAuth} className="px-4 py-2 bg-gray-900 text-white rounded">{authMode === 'login' ? 'ログイン' : '登録'}</button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
