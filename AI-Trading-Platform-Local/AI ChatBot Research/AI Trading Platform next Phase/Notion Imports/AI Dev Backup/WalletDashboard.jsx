import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { Progress } from '../ui/progress';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../ui/tabs';
import { 
  Wallet, 
  TrendingUp, 
  TrendingDown, 
  DollarSign, 
  Bitcoin, 
  Shield, 
  Activity, 
  Eye, 
  EyeOff,
  Send,
  Download,
  Settings,
  RefreshCw,
  AlertCircle,
  CheckCircle,
  Clock,
  ArrowUpRight,
  ArrowDownLeft,
  Zap,
  Lock,
  Globe,
  BarChart3,
  PieChart,
  History,
  Atom,
  Network,
  Key,
  Fingerprint,
  Layers,
  Copy,
  QrCode
} from 'lucide-react';

const WalletDashboard = ({ walletData, onOpenSettings, onOpenWalletSetup }) => {
  const [balanceVisible, setBalanceVisible] = useState(true);
  const [isLoading, setIsLoading] = useState(false);
  const [transactions, setTransactions] = useState([]);
  const [selectedWallet, setSelectedWallet] = useState('cold');
  const [quantumStrength, setQuantumStrength] = useState(87);
  const [isConnected, setIsConnected] = useState(true);
  const [showPrivateKey, setShowPrivateKey] = useState(false);

  // Simulate quantum strength fluctuation
  useEffect(() => {
    const interval = setInterval(() => {
      setQuantumStrength(prev => {
        const change = (Math.random() - 0.5) * 4;
        return Math.max(75, Math.min(100, prev + change));
      });
    }, 2000);
    return () => clearInterval(interval);
  }, []);

  const wallets = [
    {
      id: 'cold',
      name: 'Cold Storage Vault',
      type: 'Hardware',
      balance: '2.4567 BTC',
      usdValue: '$127,543.21',
      security: 'Quantum-Secured',
      status: 'Offline',
      icon: <Lock className="w-5 h-5" />,
      color: 'bg-blue-500'
    },
    {
      id: 'hot',
      name: 'Trading Wallet',
      type: 'Hot Wallet',
      balance: '0.8923 BTC',
      usdValue: '$46,234.12',
      security: 'Multi-Sig',
      status: 'Online',
      icon: <Zap className="w-5 h-5" />,
      color: 'bg-green-500'
    },
    {
      id: 'hybrid',
      name: 'Hybrid Vault',
      type: 'Smart Contract',
      balance: '1.2341 ETH',
      usdValue: '$3,892.45',
      security: 'Quantum + Multi-Sig',
      status: 'Protected',
      icon: <Layers className="w-5 h-5" />,
      color: 'bg-purple-500'
    }
  ];

  const quantumMetrics = [
    { label: 'Entanglement Pairs', value: '2,048', status: 'active' },
    { label: 'Key Rotation', value: '12h', status: 'scheduled' },
    { label: 'Quantum Signatures', value: '156', status: 'verified' },
    { label: 'Security Level', value: '256-bit', status: 'maximum' }
  ];

  const getQuantumColor = () => {
    if (quantumStrength >= 90) return 'text-green-500';
    if (quantumStrength >= 80) return 'text-yellow-500';
    return 'text-red-500';
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'active': return <CheckCircle className="w-4 h-4 text-green-500" />;
      case 'scheduled': return <Clock className="w-4 h-4 text-yellow-500" />;
      case 'verified': return <Shield className="w-4 h-4 text-blue-500" />;
      case 'maximum': return <Atom className="w-4 h-4 text-purple-500" />;
      default: return <Activity className="w-4 h-4 text-gray-500" />;
    }
  };

  // Mock transaction data
  useEffect(() => {
    const mockTransactions = [
      {
        id: '1',
        type: 'buy',
        asset: 'BTC',
        amount: 0.05,
        price: 42000,
        value: 2100,
        timestamp: new Date(Date.now() - 2 * 60 * 60 * 1000),
        status: 'completed'
      },
      {
        id: '2',
        type: 'sell',
        asset: 'ETH',
        amount: 0.5,
        price: 2400,
        value: 1200,
        timestamp: new Date(Date.now() - 5 * 60 * 60 * 1000),
        status: 'completed'
      },
      {
        id: '3',
        type: 'deposit',
        asset: 'USDT',
        amount: 500,
        price: 1,
        value: 500,
        timestamp: new Date(Date.now() - 24 * 60 * 60 * 1000),
        status: 'pending'
      }
    ];
    setTransactions(mockTransactions);
  }, []);

  const refreshBalances = async () => {
    setIsLoading(true);
    // Simulate API call
    await new Promise(resolve => setTimeout(resolve, 1500));
    setIsLoading(false);
  };

  const formatCurrency = (amount) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD'
    }).format(amount);
  };

  const getTransactionIcon = (type) => {
    switch (type) {
      case 'buy':
        return <ArrowDownLeft className="h-4 w-4 text-green-600" />;
      case 'sell':
        return <ArrowUpRight className="h-4 w-4 text-red-600" />;
      case 'deposit':
        return <Download className="h-4 w-4 text-blue-600" />;
      case 'withdraw':
        return <Send className="h-4 w-4 text-orange-600" />;
      default:
        return <Activity className="h-4 w-4 text-gray-600" />;
    }
  };

  const getStatusBadge = (status) => {
    switch (status) {
      case 'completed':
        return <Badge variant="default" className="bg-green-100 text-green-800">Completed</Badge>;
      case 'pending':
        return <Badge variant="secondary" className="bg-yellow-100 text-yellow-800">Pending</Badge>;
      case 'failed':
        return <Badge variant="destructive">Failed</Badge>;
      default:
        return <Badge variant="outline">{status}</Badge>;
    }
  };

  // Always show the quantum wallet interface instead of the "no wallet" state
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-blue-900 to-slate-900 text-white p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <div className="p-3 bg-blue-600 rounded-lg">
                <Atom className="w-8 h-8" />
              </div>
              <div>
                <h1 className="text-3xl font-bold">Quantum Wallet Interface</h1>
                <p className="text-slate-300">Military-grade quantum security for digital assets</p>
              </div>
            </div>
            <div className="flex items-center space-x-4">
              <Badge variant={isConnected ? "default" : "destructive"} className="px-3 py-1">
                <Network className="w-4 h-4 mr-2" />
                {isConnected ? 'Connected' : 'Disconnected'}
              </Badge>
              <Button variant="outline" size="sm">
                <QrCode className="w-4 h-4 mr-2" />
                Scan QR
              </Button>
            </div>
          </div>
        </div>

        {/* Quantum Security Status */}
        <Card className="mb-6 bg-slate-800/50 border-slate-700">
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <Atom className={`w-6 h-6 ${getQuantumColor()}`} />
              <span>Quantum Security Status</span>
              <Badge variant="outline" className={`ml-auto ${getQuantumColor()}`}>
                {quantumStrength.toFixed(1)}% Strength
              </Badge>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div>
                <div className="flex justify-between text-sm mb-2">
                  <span>Quantum Entanglement</span>
                  <span className={getQuantumColor()}>{quantumStrength.toFixed(1)}%</span>
                </div>
                <Progress value={quantumStrength} className="h-2" />
              </div>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {quantumMetrics.map((metric, index) => (
                  <div key={index} className="bg-slate-700/50 p-3 rounded-lg">
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-xs text-slate-400">{metric.label}</span>
                      {getStatusIcon(metric.status)}
                    </div>
                    <div className="text-lg font-semibold">{metric.value}</div>
                  </div>
                ))}
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Wallet Tabs */}
        <Tabs value={selectedWallet} onValueChange={setSelectedWallet} className="space-y-6">
          <TabsList className="grid w-full grid-cols-3 bg-slate-800">
            {wallets.map((wallet) => (
              <TabsTrigger 
                key={wallet.id} 
                value={wallet.id}
                className="data-[state=active]:bg-blue-600"
              >
                <div className="flex items-center space-x-2">
                  {wallet.icon}
                  <span className="hidden sm:inline">{wallet.name}</span>
                </div>
              </TabsTrigger>
            ))}
          </TabsList>

          {wallets.map((wallet) => (
            <TabsContent key={wallet.id} value={wallet.id}>
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* Wallet Overview */}
                <div className="lg:col-span-2 space-y-6">
                  <Card className="bg-slate-800/50 border-slate-700">
                    <CardHeader>
                      <CardTitle className="flex items-center space-x-3">
                        <div className={`p-2 ${wallet.color} rounded-lg`}>
                          {wallet.icon}
                        </div>
                        <div>
                          <div>{wallet.name}</div>
                          <CardDescription>{wallet.type} • {wallet.security}</CardDescription>
                        </div>
                        <Badge 
                          variant={wallet.status === 'Online' ? 'default' : 'secondary'}
                          className="ml-auto"
                        >
                          {wallet.status}
                        </Badge>
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="space-y-4">
                        <div className="grid grid-cols-2 gap-4">
                          <div>
                            <div className="text-sm text-slate-400 mb-1">Balance</div>
                            <div className="text-2xl font-bold">{wallet.balance}</div>
                          </div>
                          <div>
                            <div className="text-sm text-slate-400 mb-1">USD Value</div>
                            <div className="text-2xl font-bold text-green-400">{wallet.usdValue}</div>
                          </div>
                        </div>
                        
                        <div className="flex space-x-2">
                          <Button className="flex-1">
                            <TrendingUp className="w-4 h-4 mr-2" />
                            Send
                          </Button>
                          <Button variant="outline" className="flex-1">
                            <Wallet className="w-4 h-4 mr-2" />
                            Receive
                          </Button>
                          <Button variant="outline" size="icon">
                            <Copy className="w-4 h-4" />
                          </Button>
                        </div>
                      </div>
                    </CardContent>
                  </Card>

                  {/* Security Features */}
                  <Card className="bg-slate-800/50 border-slate-700">
                    <CardHeader>
                      <CardTitle className="flex items-center space-x-2">
                        <Shield className="w-5 h-5" />
                        <span>Security Features</span>
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div className="space-y-3">
                          <div className="flex items-center justify-between p-3 bg-slate-700/50 rounded-lg">
                            <div className="flex items-center space-x-2">
                              <Fingerprint className="w-4 h-4 text-blue-400" />
                              <span className="text-sm">Biometric Lock</span>
                            </div>
                            <CheckCircle className="w-4 h-4 text-green-500" />
                          </div>
                          <div className="flex items-center justify-between p-3 bg-slate-700/50 rounded-lg">
                            <div className="flex items-center space-x-2">
                              <Key className="w-4 h-4 text-purple-400" />
                              <span className="text-sm">Multi-Signature</span>
                            </div>
                            <CheckCircle className="w-4 h-4 text-green-500" />
                          </div>
                        </div>
                        <div className="space-y-3">
                          <div className="flex items-center justify-between p-3 bg-slate-700/50 rounded-lg">
                            <div className="flex items-center space-x-2">
                              <Atom className="w-4 h-4 text-cyan-400" />
                              <span className="text-sm">Quantum Encryption</span>
                            </div>
                            <CheckCircle className="w-4 h-4 text-green-500" />
                          </div>
                          <div className="flex items-center justify-between p-3 bg-slate-700/50 rounded-lg">
                            <div className="flex items-center space-x-2">
                              <AlertCircle className="w-4 h-4 text-yellow-400" />
                              <span className="text-sm">Threat Detection</span>
                            </div>
                            <CheckCircle className="w-4 h-4 text-green-500" />
                          </div>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                </div>

                {/* Quantum Indicators Panel */}
                <div className="space-y-6">
                  <Card className="bg-slate-800/50 border-slate-700">
                    <CardHeader>
                      <CardTitle className="text-lg">Quantum Indicators</CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-4">
                      <div className="text-center">
                        <div className="relative w-24 h-24 mx-auto mb-4">
                          <div className="absolute inset-0 rounded-full border-4 border-slate-600"></div>
                          <div 
                            className={`absolute inset-0 rounded-full border-4 border-t-transparent transition-all duration-1000 ${getQuantumColor().replace('text-', 'border-')}`}
                            style={{ 
                              transform: `rotate(${(quantumStrength / 100) * 360}deg)`,
                              borderTopColor: 'transparent'
                            }}
                          ></div>
                          <div className="absolute inset-0 flex items-center justify-center">
                            <Atom className={`w-8 h-8 ${getQuantumColor()}`} />
                          </div>
                        </div>
                        <div className="text-sm text-slate-400">Entanglement Strength</div>
                        <div className={`text-xl font-bold ${getQuantumColor()}`}>
                          {quantumStrength.toFixed(1)}%
                        </div>
                      </div>

                      <div className="space-y-2">
                        <div className="flex justify-between text-sm">
                          <span className="text-slate-400">Key Pairs</span>
                          <span className="text-green-400">2,048 Active</span>
                        </div>
                        <div className="flex justify-between text-sm">
                          <span className="text-slate-400">Last Rotation</span>
                          <span className="text-blue-400">2h ago</span>
                        </div>
                        <div className="flex justify-between text-sm">
                          <span className="text-slate-400">Next Rotation</span>
                          <span className="text-yellow-400">10h</span>
                        </div>
                        <div className="flex justify-between text-sm">
                          <span className="text-slate-400">Signatures</span>
                          <span className="text-purple-400">156 Verified</span>
                        </div>
                      </div>
                    </CardContent>
                  </Card>

                  <Card className="bg-slate-800/50 border-slate-700">
                    <CardHeader>
                      <CardTitle className="text-lg">Hardware Integration</CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-3">
                      <div className="flex items-center justify-between p-2 bg-slate-700/50 rounded">
                        <span className="text-sm">Ledger Nano X</span>
                        <Badge variant="outline" className="text-green-400 border-green-400">
                          Connected
                        </Badge>
                      </div>
                      <div className="flex items-center justify-between p-2 bg-slate-700/50 rounded">
                        <span className="text-sm">Trezor Model T</span>
                        <Badge variant="outline" className="text-slate-400 border-slate-400">
                          Available
                        </Badge>
                      </div>
                      <div className="flex items-center justify-between p-2 bg-slate-700/50 rounded">
                        <span className="text-sm">YubiKey 5C</span>
                        <Badge variant="outline" className="text-green-400 border-green-400">
                          Active
                        </Badge>
                      </div>
                    </CardContent>
                  </Card>

                  <Card className="bg-slate-800/50 border-slate-700">
                    <CardHeader>
                      <CardTitle className="text-lg">Private Key</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="space-y-3">
                        <div className="flex items-center space-x-2">
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => setShowPrivateKey(!showPrivateKey)}
                          >
                            {showPrivateKey ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                          </Button>
                          <span className="text-sm text-slate-400">
                            {showPrivateKey ? 'Hide' : 'Show'} Private Key
                          </span>
                        </div>
                        <div className="p-3 bg-slate-900 rounded font-mono text-xs break-all">
                          {showPrivateKey 
                            ? 'L1aW4aubDFB32xmRSz2LC4o5x6vVeAUHDm4xGG1QqDCZFxYSDbEE'
                            : '••••••••••••••••••••••••••••••••••••••••••••••••••••'
                          }
                        </div>
                        <Button variant="outline" size="sm" className="w-full">
                          <Copy className="w-4 h-4 mr-2" />
                          Copy to Clipboard
                        </Button>
                      </div>
                    </CardContent>
                  </Card>
                </div>
              </div>
            </TabsContent>
          ))}
        </Tabs>
      </div>
    </div>
  );
};

export default WalletDashboard;

