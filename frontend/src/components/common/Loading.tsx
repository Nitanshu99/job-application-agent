interface LoadingProps {
  size?: 'sm' | 'md' | 'lg';
  text?: string;
}

export const Loading = ({ size = 'md', text = 'Loading...' }: LoadingProps) => {
  const sizeClasses = {
    sm: 'w-4 h-4',
    md: 'w-8 h-8',
    lg: 'w-12 h-12',
  };

  return (
    <div className="flex items-center justify-center p-4">
      <div className="animate-spin">
        <div className={`border-4 border-gray-300 border-t-blue-600 rounded-full ${sizeClasses[size]}`} />
      </div>
      {text && <span className="ml-2 text-gray-600">{text}</span>}
    </div>
  );
};
