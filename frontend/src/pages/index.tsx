import { useEffect, useState } from 'react';
import Link from 'next/link';
import { fetchBackendData } from '@/utils/supabase';

export default function Home() {
  const [backendData, setBackendData] = useState(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const getData = async () => {
      try {
        const data = await fetchBackendData();
        setBackendData(data);
      } catch (err: unknown) {
        if (err instanceof Error) {
          setError(err.message);
        } else {
          setError('An unknown error occurred');
        }
      }
    };
    getData();
  }, []);

  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <h1 className="text-4xl font-bold text-gray-900 mb-8">Welcome to Athena</h1>
      <p className="text-lg text-gray-600 mb-8">
        Your digital executive assistant is ready to help.
      </p>
      <Link href="/dashboard" className="text-blue-600 hover:text-blue-700">
        Go to Dashboard
      </Link>
      {backendData && (
        <div className="mt-8 p-4 bg-white rounded shadow">
          <h2 className="text-xl font-semibold mb-2">Backend Data:</h2>
          <pre className="text-sm">{JSON.stringify(backendData, null, 2)}</pre>
        </div>
      )}
      {error && (
        <div className="mt-8 p-4 bg-red-100 text-red-700 rounded">
          <p>Error: {error}</p>
        </div>
      )}
    </div>
  );
}
