import React from 'react';

export default function Home() {
  return (
    <main className="flex flex-col items-center justify-center min-h-screen p-8">
      <h1 className="text-4xl font-bold mb-4">Athena Digital Executive Assistant</h1>
      <p className="text-lg text-gray-600 mb-8">Welcome to your AI-powered contact and meeting manager.</p>
      <a href="/login" className="px-6 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition">Login to Dashboard</a>
    </main>
  );
} 