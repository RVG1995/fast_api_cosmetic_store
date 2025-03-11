// components/LoadingSpinner.jsx
const LoadingSpinner = () => {
    return (
      <div className="fixed inset-0 flex items-center justify-center bg-white/75">
        <div className="animate-spin rounded-full h-16 w-16 border-t-4 border-b-4 border-blue-500"></div>
        <p className="mt-4 text-gray-700">Загрузка...</p>
      </div>
    );
  };

export default LoadingSpinner;