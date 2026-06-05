import React, { useState } from "react";
import { Database, Cpu, HardDrive, Sparkles, Cloud, Users, Code } from "lucide-react";

const AnimatedArchitecture = () => {
  const [hoveredNode, setHoveredNode] = useState(null);

  return (
    <div className="relative w-full min-h-[800px] bg-gradient-to-br from-[#0f0f1a] to-[#1a1a2e] rounded-2xl p-8 overflow-hidden border border-white/10">
      {/* Animated background grid */}
      <div className="absolute inset-0 bg-[url('data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNDAiIGhlaWdodD0iNDAiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+PGRlZnM+PHBhdHRlcm4gaWQ9ImdyaWQiIHdpZHRoPSI0MCIgaGVpZ2h0PSI0MCIgcGF0dGVyblVuaXRzPSJ1c2VyU3BhY2VPblVzZSI+PHBhdGggZD0iTSAwIDEwIEwgNDAgMTAgTSAxMCAwIEwgMTAgNDAiIGZpbGw9Im5vbmUiIHN0cm9rZT0icmdiYSgyNTUsMjU1LDI1NSwwLjAzKSIgc3Ryb2tlLXdpZHRoPSIxIi8+PC9wYXR0ZXJuPjwvZGVmcz48cmVjdCB3aWR0aD0iMTAwJSIgaGVpZ2h0PSIxMDAlIiBmaWxsPSJ1cmwoI2dyaWQpIi8+PC9zdmc+')] opacity-40" />

      {/* Animated data flow lines */}
      <svg className="absolute inset-0 w-full h-full pointer-events-none">
        {/* Customer to EC2 */}
        <path
          d="M 120 150 L 280 250"
          stroke="url(#gradient1)"
          strokeWidth="2"
          fill="none"
          strokeDasharray="5,5"
          className="animate-[dash_2s_linear_infinite]"
        />
        
        {/* EC2 to DynamoDB */}
        <path
          d="M 350 300 L 350 420"
          stroke="url(#gradient2)"
          strokeWidth="2"
          fill="none"
          strokeDasharray="5,5"
          className="animate-[dash_2s_linear_infinite]"
          style={{ animationDelay: '0.5s' }}
        />
        
        {/* EC2 to S3 */}
        <path
          d="M 380 250 L 380 180"
          stroke="url(#gradient3)"
          strokeWidth="2"
          fill="none"
          strokeDasharray="5,5"
          className="animate-[dash_2s_linear_infinite]"
          style={{ animationDelay: '1s' }}
        />
        
        {/* EC2 to Cloud Services */}
        <path
          d="M 420 280 L 650 280"
          stroke="url(#gradient4)"
          strokeWidth="2"
          fill="none"
          strokeDasharray="5,5"
          className="animate-[dash_2s_linear_infinite]"
          style={{ animationDelay: '0.3s' }}
        />
        
        {/* Gemini to S3 Vector */}
        <path
          d="M 280 520 L 480 520 L 480 180"
          stroke="url(#gradient5)"
          strokeWidth="2"
          fill="none"
          strokeDasharray="5,5"
          className="animate-[dash_2s_linear_infinite]"
          style={{ animationDelay: '1.5s' }}
        />
        
        {/* Developer to Services */}
        <path
          d="M 350 650 L 650 420"
          stroke="url(#gradient6)"
          strokeWidth="2"
          fill="none"
          strokeDasharray="5,5"
          className="animate-[dash_2s_linear_infinite]"
          style={{ animationDelay: '0.8s' }}
        />

        <defs>
          <linearGradient id="gradient1" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#8b5cf6" stopOpacity="0" />
            <stop offset="50%" stopColor="#8b5cf6" stopOpacity="1" />
            <stop offset="100%" stopColor="#8b5cf6" stopOpacity="0" />
          </linearGradient>
          <linearGradient id="gradient2" x1="0%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stopColor="#3b82f6" stopOpacity="0" />
            <stop offset="50%" stopColor="#3b82f6" stopOpacity="1" />
            <stop offset="100%" stopColor="#3b82f6" stopOpacity="0" />
          </linearGradient>
          <linearGradient id="gradient3" x1="0%" y1="100%" x2="0%" y2="0%">
            <stop offset="0%" stopColor="#10b981" stopOpacity="0" />
            <stop offset="50%" stopColor="#10b981" stopOpacity="1" />
            <stop offset="100%" stopColor="#10b981" stopOpacity="0" />
          </linearGradient>
          <linearGradient id="gradient4" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#f59e0b" stopOpacity="0" />
            <stop offset="50%" stopColor="#f59e0b" stopOpacity="1" />
            <stop offset="100%" stopColor="#f59e0b" stopOpacity="0" />
          </linearGradient>
          <linearGradient id="gradient5" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#ec4899" stopOpacity="0" />
            <stop offset="50%" stopColor="#ec4899" stopOpacity="1" />
            <stop offset="100%" stopColor="#ec4899" stopOpacity="0" />
          </linearGradient>
          <linearGradient id="gradient6" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#06b6d4" stopOpacity="0" />
            <stop offset="50%" stopColor="#06b6d4" stopOpacity="1" />
            <stop offset="100%" stopColor="#06b6d4" stopOpacity="0" />
          </linearGradient>
        </defs>
      </svg>

      {/* Architecture Nodes */}
      <div className="relative z-10">
        {/* Customer Node */}
        <div 
          className="absolute top-20 left-8"
          onMouseEnter={() => setHoveredNode('customer')}
          onMouseLeave={() => setHoveredNode(null)}
        >
          <div className={`transition-all duration-300 ${hoveredNode === 'customer' ? 'scale-110' : ''}`}>
            <div className="w-24 h-24 bg-gradient-to-br from-purple-500/20 to-purple-600/10 backdrop-blur-sm border-2 border-purple-500/50 rounded-xl flex flex-col items-center justify-center shadow-lg shadow-purple-500/20 hover:shadow-purple-500/40 transition-all">
              <Users className="w-10 h-10 text-purple-400 mb-1" />
              <span className="text-xs font-semibold text-white">Customer</span>
            </div>
            {hoveredNode === 'customer' && (
              <div className="absolute top-full mt-2 left-1/2 transform -translate-x-1/2 bg-gray-900/95 backdrop-blur-sm border border-purple-500/30 rounded-lg p-3 w-48 text-xs text-gray-300 shadow-xl z-50">
                End users accessing the Virtual Dealer platform
              </div>
            )}
          </div>
        </div>

        {/* EC2 Instance Container */}
        <div 
          className="absolute top-32 left-32 w-80 h-64 bg-gradient-to-br from-orange-900/20 to-orange-800/10 backdrop-blur-sm border-2 border-orange-500/40 rounded-2xl p-4 shadow-2xl"
          onMouseEnter={() => setHoveredNode('ec2')}
          onMouseLeave={() => setHoveredNode(null)}
        >
          <div className="flex items-center gap-2 mb-4">
            <Cpu className="w-6 h-6 text-orange-400" />
            <span className="text-sm font-bold text-white">EC2 Instance</span>
          </div>

          {/* Nginx Badge */}
          <div className="absolute -top-3 right-4 bg-orange-600/90 backdrop-blur-sm border border-orange-400/50 rounded-full px-3 py-1 text-xs font-semibold text-white shadow-lg">
            Nginx
          </div>

          {hoveredNode === 'ec2' && (
            <div className="absolute top-full mt-2 left-0 bg-gray-900/95 backdrop-blur-sm border border-orange-500/30 rounded-lg p-3 w-72 text-xs text-gray-300 shadow-xl z-50">
              Central server hosting both frontend and backend services behind Nginx reverse proxy
            </div>
          )}

          {/* Frontend */}
          <div className="mb-3 bg-blue-900/20 border border-blue-500/30 rounded-lg p-3 hover:bg-blue-900/30 transition-all">
            <div className="flex items-center gap-2 mb-1">
              <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-blue-600 rounded-lg flex items-center justify-center">
                <Code className="w-4 h-4 text-white" />
              </div>
              <div>
                <div className="text-xs font-semibold text-white">Frontend</div>
                <div className="text-xs text-blue-300">React :3000</div>
              </div>
            </div>
          </div>

          {/* Backend */}
          <div className="bg-purple-900/20 border border-purple-500/30 rounded-lg p-3 hover:bg-purple-900/30 transition-all">
            <div className="flex items-center gap-2 mb-1">
              <div className="w-8 h-8 bg-gradient-to-br from-purple-500 to-purple-600 rounded-lg flex items-center justify-center">
                <Cpu className="w-4 h-4 text-white" />
              </div>
              <div>
                <div className="text-xs font-semibold text-white">Backend</div>
                <div className="text-xs text-purple-300">FastAPI :8000</div>
              </div>
            </div>
          </div>
        </div>

        {/* S3 Bucket */}
        <div 
          className="absolute top-16 left-96"
          onMouseEnter={() => setHoveredNode('s3')}
          onMouseLeave={() => setHoveredNode(null)}
        >
          <div className={`transition-all duration-300 ${hoveredNode === 's3' ? 'scale-110' : ''}`}>
            <div className="w-24 h-24 bg-gradient-to-br from-green-500/20 to-green-600/10 backdrop-blur-sm border-2 border-green-500/50 rounded-xl flex flex-col items-center justify-center shadow-lg shadow-green-500/20 hover:shadow-green-500/40 transition-all">
              <HardDrive className="w-10 h-10 text-green-400 mb-1" />
              <span className="text-xs font-semibold text-white text-center">S3</span>
            </div>
            {hoveredNode === 's3' && (
              <div className="absolute top-full mt-2 left-1/2 transform -translate-x-1/2 bg-gray-900/95 backdrop-blur-sm border border-green-500/30 rounded-lg p-3 w-48 text-xs text-gray-300 shadow-xl z-50">
                Object storage for vector indices and RAG payloads
              </div>
            )}
          </div>
        </div>

        {/* S3 Vector */}
        <div 
          className="absolute top-16 right-72"
          onMouseEnter={() => setHoveredNode('s3vector')}
          onMouseLeave={() => setHoveredNode(null)}
        >
          <div className={`transition-all duration-300 ${hoveredNode === 's3vector' ? 'scale-110' : ''}`}>
            <div className="w-28 h-24 bg-gradient-to-br from-green-500/20 to-green-600/10 backdrop-blur-sm border-2 border-green-500/50 rounded-xl flex flex-col items-center justify-center shadow-lg shadow-green-500/20 hover:shadow-green-500/40 transition-all">
              <HardDrive className="w-10 h-10 text-green-400 mb-1" />
              <span className="text-xs font-semibold text-white text-center">S3 Vector</span>
            </div>
            {hoveredNode === 's3vector' && (
              <div className="absolute top-full mt-2 left-1/2 transform -translate-x-1/2 bg-gray-900/95 backdrop-blur-sm border border-green-500/30 rounded-lg p-3 w-48 text-xs text-gray-300 shadow-xl z-50">
                Vector embeddings storage for semantic search
              </div>
            )}
          </div>
        </div>

        {/* DynamoDB */}
        <div 
          className="absolute top-80 left-48"
          onMouseEnter={() => setHoveredNode('dynamodb')}
          onMouseLeave={() => setHoveredNode(null)}
        >
          <div className={`transition-all duration-300 ${hoveredNode === 'dynamodb' ? 'scale-110' : ''}`}>
            <div className="w-28 h-28 bg-gradient-to-br from-blue-500/20 to-blue-600/10 backdrop-blur-sm border-2 border-blue-500/50 rounded-xl flex flex-col items-center justify-center shadow-lg shadow-blue-500/20 hover:shadow-blue-500/40 transition-all">
              <Database className="w-12 h-12 text-blue-400 mb-1" />
              <span className="text-xs font-semibold text-white text-center">DynamoDB</span>
            </div>
            {hoveredNode === 'dynamodb' && (
              <div className="absolute top-full mt-2 left-1/2 transform -translate-x-1/2 bg-gray-900/95 backdrop-blur-sm border border-blue-500/30 rounded-lg p-3 w-48 text-xs text-gray-300 shadow-xl z-50">
                NoSQL database storing chat logs and session data
              </div>
            )}
          </div>
        </div>

        {/* Gemini Embedding */}
        <div 
          className="absolute top-[450px] left-16"
          onMouseEnter={() => setHoveredNode('gemini')}
          onMouseLeave={() => setHoveredNode(null)}
        >
          <div className={`transition-all duration-300 ${hoveredNode === 'gemini' ? 'scale-110' : ''}`}>
            <div className="w-32 h-28 bg-gradient-to-br from-pink-500/20 to-pink-600/10 backdrop-blur-sm border-2 border-pink-500/50 rounded-xl flex flex-col items-center justify-center shadow-lg shadow-pink-500/20 hover:shadow-pink-500/40 transition-all relative">
              <Sparkles className="w-10 h-10 text-pink-400 mb-1 animate-pulse" />
              <span className="text-xs font-semibold text-white text-center">Gemini</span>
              <span className="text-xs text-pink-300">Embedding 2</span>
            </div>
            {hoveredNode === 'gemini' && (
              <div className="absolute top-full mt-2 left-1/2 transform -translate-x-1/2 bg-gray-900/95 backdrop-blur-sm border border-pink-500/30 rounded-lg p-3 w-48 text-xs text-gray-300 shadow-xl z-50">
                Google's embedding model for converting text to vectors
              </div>
            )}
          </div>
        </div>

        {/* Cloud Services Container */}
        <div className="absolute top-8 right-8 w-72 h-[500px] bg-gradient-to-br from-gray-800/20 to-gray-900/10 backdrop-blur-sm border-2 border-gray-500/30 rounded-2xl p-4 shadow-2xl">
          <div className="flex items-center gap-2 mb-4">
            <Cloud className="w-6 h-6 text-gray-400" />
            <span className="text-sm font-bold text-white">Cloud Services</span>
          </div>

          {/* CloudWatch */}
          <div 
            className="mb-4 bg-pink-900/20 border border-pink-500/30 rounded-lg p-3 hover:bg-pink-900/30 transition-all cursor-pointer"
            onMouseEnter={() => setHoveredNode('cloudwatch')}
            onMouseLeave={() => setHoveredNode(null)}
          >
            <div className="flex items-center gap-2">
              <div className="w-10 h-10 bg-pink-600 rounded flex items-center justify-center text-white font-bold text-xs">
                CW
              </div>
              <div className="flex-1">
                <div className="text-xs font-semibold text-white">Cloud Watch</div>
                <div className="text-xs text-pink-300">Monitoring</div>
              </div>
            </div>
            {hoveredNode === 'cloudwatch' && (
              <div className="mt-2 text-xs text-gray-300 bg-gray-900/50 rounded p-2">
                Real-time monitoring and metrics collection
              </div>
            )}
          </div>

          {/* Claude */}
          <div 
            className="mb-4 bg-orange-900/20 border border-orange-500/30 rounded-lg p-3 hover:bg-orange-900/30 transition-all cursor-pointer"
            onMouseEnter={() => setHoveredNode('claude')}
            onMouseLeave={() => setHoveredNode(null)}
          >
            <div className="flex items-center gap-2">
              <div className="w-10 h-10 bg-gradient-to-br from-orange-500 to-amber-500 rounded flex items-center justify-center">
                <Sparkles className="w-6 h-6 text-white" />
              </div>
              <div className="flex-1">
                <div className="text-xs font-semibold text-white">Claude</div>
                <div className="text-xs text-orange-300">LLM</div>
              </div>
            </div>
            {hoveredNode === 'claude' && (
              <div className="mt-2 text-xs text-gray-300 bg-gray-900/50 rounded p-2">
                Anthropic's AI model powering Aria chatbot
              </div>
            )}
          </div>

          {/* Langfuse */}
          <div 
            className="mb-4 bg-red-900/20 border border-red-500/30 rounded-lg p-3 hover:bg-red-900/30 transition-all cursor-pointer"
            onMouseEnter={() => setHoveredNode('langfuse')}
            onMouseLeave={() => setHoveredNode(null)}
          >
            <div className="flex items-center gap-2">
              <div className="w-10 h-10 bg-red-600 rounded flex items-center justify-center">
                <div className="text-white font-bold text-xs">LF</div>
              </div>
              <div className="flex-1">
                <div className="text-xs font-semibold text-white">Langfuse</div>
                <div className="text-xs text-red-300">Observability</div>
              </div>
            </div>
            {hoveredNode === 'langfuse' && (
              <div className="mt-2 text-xs text-gray-300 bg-gray-900/50 rounded p-2">
                LLM application tracing and monitoring
              </div>
            )}
          </div>

          {/* Agora */}
          <div 
            className="mb-4 bg-cyan-900/20 border border-cyan-500/30 rounded-lg p-3 hover:bg-cyan-900/30 transition-all cursor-pointer"
            onMouseEnter={() => setHoveredNode('agora')}
            onMouseLeave={() => setHoveredNode(null)}
          >
            <div className="flex items-center gap-2">
              <div className="w-10 h-10 bg-cyan-500 rounded flex items-center justify-center text-white font-bold text-lg">
                A
              </div>
              <div className="flex-1">
                <div className="text-xs font-semibold text-white">Agora</div>
                <div className="text-xs text-cyan-300">Voice RTC</div>
              </div>
            </div>
            {hoveredNode === 'agora' && (
              <div className="mt-2 text-xs text-gray-300 bg-gray-900/50 rounded p-2">
                Real-time voice communication service
              </div>
            )}
          </div>

          {/* Minimax */}
          <div 
            className="bg-pink-900/20 border border-pink-500/30 rounded-lg p-3 hover:bg-pink-900/30 transition-all cursor-pointer"
            onMouseEnter={() => setHoveredNode('minimax')}
            onMouseLeave={() => setHoveredNode(null)}
          >
            <div className="flex items-center gap-2">
              <div className="w-10 h-10 bg-gradient-to-br from-pink-500 to-pink-600 rounded flex items-center justify-center">
                <div className="text-white font-bold text-xs">MM</div>
              </div>
              <div className="flex-1">
                <div className="text-xs font-semibold text-white">Minimax</div>
                <div className="text-xs text-pink-300">TTS</div>
              </div>
            </div>
            {hoveredNode === 'minimax' && (
              <div className="mt-2 text-xs text-gray-300 bg-gray-900/50 rounded p-2">
                Text-to-speech voice synthesis
              </div>
            )}
          </div>
        </div>

        {/* Developer Node */}
        <div 
          className="absolute bottom-8 left-1/3"
          onMouseEnter={() => setHoveredNode('developer')}
          onMouseLeave={() => setHoveredNode(null)}
        >
          <div className={`transition-all duration-300 ${hoveredNode === 'developer' ? 'scale-110' : ''}`}>
            <div className="w-24 h-24 bg-gradient-to-br from-cyan-500/20 to-cyan-600/10 backdrop-blur-sm border-2 border-cyan-500/50 rounded-xl flex flex-col items-center justify-center shadow-lg shadow-cyan-500/20 hover:shadow-cyan-500/40 transition-all">
              <Code className="w-10 h-10 text-cyan-400 mb-1" />
              <span className="text-xs font-semibold text-white">Developer</span>
            </div>
            {hoveredNode === 'developer' && (
              <div className="absolute bottom-full mb-2 left-1/2 transform -translate-x-1/2 bg-gray-900/95 backdrop-blur-sm border border-cyan-500/30 rounded-lg p-3 w-48 text-xs text-gray-300 shadow-xl z-50">
                Development and monitoring access to all services
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Legend */}
      <div className="absolute bottom-4 left-4 bg-gray-900/80 backdrop-blur-sm border border-white/10 rounded-lg p-3 text-xs text-gray-400">
        <div className="font-semibold text-white mb-2">Data Flow</div>
        <div className="flex items-center gap-2 mb-1">
          <div className="w-4 h-0.5 bg-gradient-to-r from-purple-500 to-blue-500"></div>
          <span>Request/Response</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-4 h-0.5 bg-gradient-to-r from-green-500 to-pink-500"></div>
          <span>Data Storage</span>
        </div>
      </div>

      <style jsx>{`
        @keyframes dash {
          to {
            stroke-dashoffset: -10;
          }
        }
      `}</style>
    </div>
  );
};

export default AnimatedArchitecture;
