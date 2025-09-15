import { useRef, useEffect, useState } from "react";
import { Search, Plus, MoreHorizontal, Filter, Calendar, User } from "lucide-react";

export default function Home() {
  // 状態管理
  const [currentView, setCurrentView] = useState("tasks");
  const [tasks, setTasks] = useState([
    {id: 1, title: "プレゼン資料作成", status: "active", category: "work", dueDate: "9/16"},
    {id: 2, title: "英語の宿題", status: "pending", category: "study", dueDate: "9/17"},
    {id: 3, title: "部屋の掃除", status: "done", category: "personal", dueDate: "9/15"},
    {id: 4, title: "ジムに行く", status: "pending", category: "health", dueDate: "9/16"},
    {id: 5, title: "買い物リスト作成", status: "active", category: "personal", dueDate: "9/18"}
  ]);
  
  const [newTask, setNewTask] = useState("");
  const [selectedFilter, setSelectedFilter] = useState("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [showAddForm, setShowAddForm] = useState(false);

  // フィルター処理
  const filteredTasks = tasks.filter(task => {
    const matchesSearch = task.title.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesFilter = selectedFilter === "all" || task.status === selectedFilter;
    return matchesSearch && matchesFilter;
  });

  const addTask = () => {
    if (!newTask.trim()) return;
    const task = {
      id: Date.now(),
      title: newTask,
      status: "pending",
      category: "personal",
      dueDate: new Date().toLocaleDateString('ja-JP', {month: 'numeric', day: 'numeric'})
    };
    setTasks([...tasks, task]);
    setNewTask("");
    setShowAddForm(false);
  };

  const updateTaskStatus = (taskId: number, newStatus: string) => {
    setTasks(tasks.map(task => 
      task.id === taskId ? {...task, status: newStatus} : task
    ));
  };

  const deleteTask = (taskId: number) => {
    setTasks(tasks.filter(task => task.id !== taskId));
  };

  const getStatusColor = (status: string) => {
    switch(status) {
      case "done": return "bg-green-100 text-green-800";
      case "active": return "bg-blue-100 text-blue-800";
      case "pending": return "bg-gray-100 text-gray-600";
      default: return "bg-gray-100 text-gray-600";
    }
  };

  const getCategoryColor = (category: string) => {
    switch(category) {
      case "work": return "border-l-red-500";
      case "study": return "border-l-blue-500";
      case "personal": return "border-l-purple-500";
      case "health": return "border-l-green-500";
      default: return "border-l-gray-300";
    }
  };

  return (
    <div className="min-h-screen bg-white">
      {/* ヘッダー */}
      <header className="border-b border-gray-200 bg-white sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center space-x-4">
              <h1 className="text-xl font-semibold text-gray-900">Sista</h1>
              <nav className="flex space-x-8">
                <button 
                  onClick={() => setCurrentView("tasks")}
                  className={`text-sm font-medium ${currentView === "tasks" ? "text-gray-900 border-b-2 border-gray-900" : "text-gray-500 hover:text-gray-700"} pb-4`}
                >
                  タスク
                </button>
                <button 
                  onClick={() => setCurrentView("calendar")}
                  className={`text-sm font-medium ${currentView === "calendar" ? "text-gray-900 border-b-2 border-gray-900" : "text-gray-500 hover:text-gray-700"} pb-4`}
                >
                  カレンダー
                </button>
                <button 
                  onClick={() => setCurrentView("chat")}
                  className={`text-sm font-medium ${currentView === "chat" ? "text-gray-900 border-b-2 border-gray-900" : "text-gray-500 hover:text-gray-700"} pb-4`}
                >
                  アシスタント
                </button>
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
            {/* コントロール */}
            <div className="flex justify-between items-center">
              <div className="flex items-center space-x-4">
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
                  <input
                    type="text"
                    placeholder="タスクを検索..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="pl-10 pr-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent w-64"
                  />
                </div>
                <select 
                  value={selectedFilter}
                  onChange={(e) => setSelectedFilter(e.target.value)}
                  className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="all">すべて</option>
                  <option value="active">進行中</option>
                  <option value="pending">未着手</option>
                  <option value="done">完了</option>
                </select>
              </div>
              <button 
                onClick={() => setShowAddForm(!showAddForm)}
                className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-gray-900 hover:bg-gray-800 focus:outline-none focus:ring-2 focus:ring-gray-500"
              >
                <Plus className="w-4 h-4 mr-2" />
                新規タスク
              </button>
            </div>

            {/* 新規タスク追加フォーム */}
            {showAddForm && (
              <div className="bg-gray-50 p-4 rounded-lg border border-gray-200">
                <div className="flex space-x-3">
                  <input
                    type="text"
                    placeholder="タスクを入力..."
                    value={newTask}
                    onChange={(e) => setNewTask(e.target.value)}
                    className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    onKeyPress={(e) => e.key === "Enter" && addTask()}
                    autoFocus
                  />
                  <button 
                    onClick={addTask}
                    className="px-4 py-2 bg-gray-900 text-white text-sm rounded-md hover:bg-gray-800"
                  >
                    追加
                  </button>
                  <button 
                    onClick={() => {setShowAddForm(false); setNewTask("");}}
                    className="px-4 py-2 border border-gray-300 text-gray-700 text-sm rounded-md hover:bg-gray-50"
                  >
                    キャンセル
                  </button>
                </div>
              </div>
            )}

            {/* タスクリスト */}
            <div className="space-y-2">
              {filteredTasks.map(task => (
                <div key={task.id} className={`bg-white border border-gray-200 hover:border-gray-300 transition-colors border-l-4 ${getCategoryColor(task.category)}`}>
                  <div className="px-4 py-3">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center space-x-3 flex-1">
                        <input
                          type="checkbox"
                          checked={task.status === "done"}
                          onChange={(e) => updateTaskStatus(task.id, e.target.checked ? "done" : "pending")}
                          className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                        />
                        <div className="flex-1">
                          <h3 className={`text-sm font-medium ${task.status === "done" ? "line-through text-gray-500" : "text-gray-900"}`}>
                            {task.title}
                          </h3>
                          <div className="flex items-center space-x-2 mt-1">
                            <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(task.status)}`}>
                              {task.status === "done" ? "完了" : task.status === "active" ? "進行中" : "未着手"}
                            </span>
                            <span className="text-xs text-gray-500">{task.dueDate}</span>
                          </div>
                        </div>
                      </div>
                      <div className="flex items-center space-x-2">
                        {task.status !== "done" && (
                          <button 
                            onClick={() => updateTaskStatus(task.id, task.status === "active" ? "pending" : "active")}
                            className="text-xs px-2 py-1 text-blue-600 hover:bg-blue-50 rounded"
                          >
                            {task.status === "active" ? "一時停止" : "開始"}
                          </button>
                        )}
                        <button 
                          onClick={() => deleteTask(task.id)}
                          className="text-gray-400 hover:text-red-500 p-1"
                        >
                          <MoreHorizontal className="w-4 h-4" />
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>

            {filteredTasks.length === 0 && (
              <div className="text-center py-12">
                <p className="text-gray-500">タスクが見つかりません</p>
              </div>
            )}
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
                  <div className="w-8 h-8 bg-gray-200 rounded-full flex items-center justify-center">
                    <span className="text-sm font-medium text-gray-600">S</span>
                  </div>
                  <div className="flex-1">
                    <p className="text-sm text-gray-900">こんにちは！今日のタスクをチェックしましょう。</p>
                    <p className="text-xs text-gray-500 mt-1">2分前</p>
                  </div>
                </div>
                <div className="flex space-x-3">
                  <div className="w-8 h-8 bg-blue-500 rounded-full flex items-center justify-center">
                    <span className="text-sm font-medium text-white">あ</span>
                  </div>
                  <div className="flex-1">
                    <p className="text-sm text-gray-900">プレゼンの準備が思うように進まなくて...</p>
                    <p className="text-xs text-gray-500 mt-1">1分前</p>
                  </div>
                </div>
                <div className="flex space-x-3">
                  <div className="w-8 h-8 bg-gray-200 rounded-full flex items-center justify-center">
                    <span className="text-sm font-medium text-gray-600">S</span>
                  </div>
                  <div className="flex-1">
                    <p className="text-sm text-gray-900">まずは小さなステップから始めてみましょう。アウトラインを作ることから始めてはいかがですか？</p>
                    <p className="text-xs text-gray-500 mt-1">1分前</p>
                  </div>
                </div>
              </div>
              <div className="p-4 border-t border-gray-200">
                <div className="flex space-x-3">
                  <input
                    type="text"
                    placeholder="メッセージを入力..."
                    className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
                  />
                  <button className="px-4 py-2 bg-gray-900 text-white text-sm rounded-md hover:bg-gray-800">
                    送信
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}