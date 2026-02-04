import React, { useState } from 'react';
import { useKeycloak } from '@react-keycloak/web';

interface ClientSummary {
  client_id: number;
  client_external_id: string;
  client_name: string;
  client_email: string;
  client_city: string;
  client_country: string;
  registration_date: string;
  total_prostheses: number;
  active_prostheses: number;
  avg_daily_movements: number | null;
  avg_battery_level: number | null;
  avg_response_time_ms: number | null;
  total_errors_30d: number;
  last_activity_date: string | null;
  days_since_last_service: number | null;
}

interface TelemetryDaily {
  report_date: string;
  client_id: number;
  client_name: string;
  prosthesis_serial_number: string;
  prosthesis_model: string;
  avg_battery_level: number;
  min_battery_level: number;
  max_battery_level: number;
  avg_response_time_ms: number;
  min_response_time_ms: number;
  max_response_time_ms: number;
  avg_grip_strength: number;
  avg_myosignal_amplitude: number;
  total_movements_count: number;
  avg_temperature: number;
  error_count: number;
  records_count: number;
}

interface ClientReport {
  summary: ClientSummary;
  telemetry_history: TelemetryDaily[];
  data_available_until: string | null;
}

const ReportPage: React.FC = () => {
  const { keycloak, initialized } = useKeycloak();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [report, setReport] = useState<ClientReport | null>(null);
  const [days, setDays] = useState(30);

  const generateReport = async () => {
    if (!keycloak?.token) {
      setError('Not authenticated');
      return;
    }

    try {
      setLoading(true);
      setError(null);

      const response = await fetch(
        `${process.env.REACT_APP_API_URL}/reports/me?days=${days}`,
        {
          headers: {
            'Authorization': `Bearer ${keycloak.token}`,
            'Content-Type': 'application/json'
          }
        }
      );

      if (!response.ok) {
        const errorData = await response.json().catch(() => null);
        throw new Error(errorData?.detail || `Error: ${response.status}`);
      }

      const data: ClientReport = await response.json();
      setReport(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
      setReport(null);
    } finally {
      setLoading(false);
    }
  };

  if (!initialized) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (!keycloak.authenticated) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
        <div className="p-10 bg-white rounded-2xl shadow-xl max-w-md w-full mx-4">
          <div className="text-center mb-8">
            <h1 className="text-3xl font-bold text-gray-800 mb-2">BionicPRO</h1>
            <p className="text-gray-500">Reports Portal</p>
          </div>
          <button
            onClick={() => keycloak.login()}
            className="w-full px-6 py-3 bg-blue-600 text-white font-semibold rounded-lg hover:bg-blue-700 transition-colors shadow-md"
          >
            Sign In
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      <header className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 py-4 flex justify-between items-center">
          <h1 className="text-xl font-bold text-gray-800">BionicPRO Reports</h1>
          <div className="flex items-center gap-4">
            <span className="text-gray-600 text-sm">
              {keycloak.tokenParsed?.preferred_username}
            </span>
            <button
              onClick={() => keycloak.logout()}
              className="px-4 py-2 text-sm text-gray-600 hover:text-gray-800 hover:bg-gray-100 rounded-lg transition-colors"
            >
              Logout
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-8">
        <div className="bg-white rounded-xl shadow-lg p-6 mb-6">
          <h2 className="text-lg font-semibold text-gray-800 mb-4">Generate My Report</h2>
          <div className="flex flex-wrap items-end gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Period (days)
              </label>
              <select
                value={days}
                onChange={(e) => setDays(Number(e.target.value))}
                className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                <option value={7}>Last 7 days</option>
                <option value={30}>Last 30 days</option>
                <option value={90}>Last 90 days</option>
                <option value={180}>Last 180 days</option>
                <option value={365}>Last year</option>
              </select>
            </div>
            <button
              onClick={generateReport}
              disabled={loading}
              className={`px-6 py-2 bg-blue-600 text-white font-semibold rounded-lg hover:bg-blue-700 transition-colors shadow-md flex items-center gap-2 ${
                loading ? 'opacity-50 cursor-not-allowed' : ''
              }`}
            >
              {loading ? (
                <>
                  <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                  Generating...
                </>
              ) : (
                <>
                  <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                  Generate Report
                </>
              )}
            </button>
          </div>

          {error && (
            <div className="mt-4 p-4 bg-red-50 border border-red-200 text-red-700 rounded-lg">
              {error}
            </div>
          )}

          {report?.data_available_until && (
            <div className="mt-4 p-3 bg-blue-50 border border-blue-200 text-blue-700 rounded-lg text-sm">
              Data available up to: <strong>{report.data_available_until}</strong>
            </div>
          )}
        </div>

        {report && (
          <>
            <div className="bg-white rounded-xl shadow-lg p-6 mb-6">
              <h2 className="text-lg font-semibold text-gray-800 mb-4">Client Summary</h2>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                <div className="p-4 bg-gray-50 rounded-lg">
                  <p className="text-sm text-gray-500">Name</p>
                  <p className="text-lg font-medium text-gray-800">{report.summary.client_name}</p>
                </div>
                <div className="p-4 bg-gray-50 rounded-lg">
                  <p className="text-sm text-gray-500">Email</p>
                  <p className="text-lg font-medium text-gray-800">{report.summary.client_email}</p>
                </div>
                <div className="p-4 bg-gray-50 rounded-lg">
                  <p className="text-sm text-gray-500">Location</p>
                  <p className="text-lg font-medium text-gray-800">
                    {report.summary.client_city}, {report.summary.client_country}
                  </p>
                </div>
                <div className="p-4 bg-blue-50 rounded-lg">
                  <p className="text-sm text-blue-600">Total Prostheses</p>
                  <p className="text-2xl font-bold text-blue-700">{report.summary.total_prostheses}</p>
                </div>
                <div className="p-4 bg-green-50 rounded-lg">
                  <p className="text-sm text-green-600">Active Prostheses</p>
                  <p className="text-2xl font-bold text-green-700">{report.summary.active_prostheses}</p>
                </div>
                <div className="p-4 bg-yellow-50 rounded-lg">
                  <p className="text-sm text-yellow-600">Errors (30d)</p>
                  <p className="text-2xl font-bold text-yellow-700">{report.summary.total_errors_30d}</p>
                </div>
                <div className="p-4 bg-gray-50 rounded-lg">
                  <p className="text-sm text-gray-500">Avg Daily Movements</p>
                  <p className="text-lg font-medium text-gray-800">
                    {report.summary.avg_daily_movements?.toFixed(0) || 'N/A'}
                  </p>
                </div>
                <div className="p-4 bg-gray-50 rounded-lg">
                  <p className="text-sm text-gray-500">Avg Battery Level</p>
                  <p className="text-lg font-medium text-gray-800">
                    {report.summary.avg_battery_level?.toFixed(1) || 'N/A'}%
                  </p>
                </div>
                <div className="p-4 bg-gray-50 rounded-lg">
                  <p className="text-sm text-gray-500">Avg Response Time</p>
                  <p className="text-lg font-medium text-gray-800">
                    {report.summary.avg_response_time_ms?.toFixed(1) || 'N/A'} ms
                  </p>
                </div>
              </div>
            </div>

            {report.telemetry_history.length > 0 && (
              <div className="bg-white rounded-xl shadow-lg p-6">
                <h2 className="text-lg font-semibold text-gray-800 mb-4">Telemetry History</h2>
                <div className="overflow-x-auto">
                  <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Date</th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Prosthesis</th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Model</th>
                        <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">Battery</th>
                        <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">Response</th>
                        <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">Movements</th>
                        <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">Errors</th>
                      </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                      {report.telemetry_history.map((item, index) => (
                        <tr key={index} className="hover:bg-gray-50">
                          <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-900">{item.report_date}</td>
                          <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-500">{item.prosthesis_serial_number}</td>
                          <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-500">{item.prosthesis_model}</td>
                          <td className="px-4 py-3 whitespace-nowrap text-sm text-center">
                            <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                              item.avg_battery_level >= 50 ? 'bg-green-100 text-green-800' :
                              item.avg_battery_level >= 20 ? 'bg-yellow-100 text-yellow-800' :
                              'bg-red-100 text-red-800'
                            }`}>
                              {item.avg_battery_level.toFixed(0)}%
                            </span>
                          </td>
                          <td className="px-4 py-3 whitespace-nowrap text-sm text-center text-gray-500">
                            {item.avg_response_time_ms.toFixed(1)} ms
                          </td>
                          <td className="px-4 py-3 whitespace-nowrap text-sm text-center text-gray-500">
                            {item.total_movements_count}
                          </td>
                          <td className="px-4 py-3 whitespace-nowrap text-sm text-center">
                            <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                              item.error_count === 0 ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                            }`}>
                              {item.error_count}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {report.telemetry_history.length === 0 && (
              <div className="bg-white rounded-xl shadow-lg p-6 text-center">
                <p className="text-gray-500">No telemetry data available for the selected period.</p>
              </div>
            )}
          </>
        )}
      </main>
    </div>
  );
};

export default ReportPage;