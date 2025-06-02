import React from 'react';

export default function Login() {
  return (
    <main className="flex flex-col items-center justify-center min-h-screen p-8">
      <h1 className="text-3xl font-bold mb-4">Login</h1>
      <p className="mb-4 text-gray-600">Sign in to access your dashboard.</p>
      {/* Auth form or Supabase Auth UI goes here */}
      <form className="flex flex-col gap-4 w-full max-w-xs">
        <input type="email" placeholder="Email" className="border p-2 rounded" />
        <input type="password" placeholder="Password" className="border p-2 rounded" />
        <button
          type="submit"
          className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 transition"
        >
          Sign In
        </button>
      </form>
    </main>
  );
}
