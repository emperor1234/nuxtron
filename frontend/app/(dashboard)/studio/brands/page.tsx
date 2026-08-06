/**
 * Brand Hub Manager
 *
 * Multi-brand management:
 * - Create/edit brands
 * - Set brand guidelines
 * - Manage asset library
 * - Team collaboration
 * - Brand analytics
 */

'use client';

import { useState, useEffect } from 'react';
import { apiGet, apiSend, DEFAULT_TENANT_ID } from '@/app/lib/platform-api';

interface Brand {
  id: string;
  name: string;
  description: string;
  status: string;
  website?: string;
  assets_count: number;
  team_size: number;
  created_at: string;
}

interface BrandDetail extends Brand {
  guidelines: {
    primary_color: string;
    secondary_color: string;
    tone: string;
    required_keywords: string[];
    restricted_keywords: string[];
    version: number;
  };
  team: {
    owners: string[];
    contributors: string[];
  };
  updated_at: string;
}

interface BrandAsset {
  id: string;
  name: string;
  type: string;
  category: string;
  usage_count: number;
  last_used?: string;
}

export default function BrandHubManager() {
  const [brands, setBrands] = useState<Brand[]>([]);
  const [selectedBrand, setSelectedBrand] = useState<BrandDetail | null>(null);
  const [assets, setAssets] = useState<BrandAsset[]>([]);
  const [loading, setLoading] = useState(false);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [showAssetForm, setShowAssetForm] = useState(false);
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    website: '',
  });
  const [assetData, setAssetData] = useState({
    name: '',
    asset_type: 'image',
    url: '',
    category: 'general',
  });

  useEffect(() => {
    fetchBrands();
  }, []);

  const fetchBrands = async () => {
    try {
      setLoading(true);
      const response = await apiGet<{ brands?: Brand[] }>('/api/v1/brands', DEFAULT_TENANT_ID);
      setBrands(response.brands || []);
    } catch (error) {
      console.error('Failed to fetch brands:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchBrandDetail = async (brandId: string) => {
    try {
      const response = await apiGet<BrandDetail>(`/api/v1/brands/${brandId}`, DEFAULT_TENANT_ID);
      setSelectedBrand(response);

      // Also fetch assets
      const assetsResponse = await apiGet<{ assets?: BrandAsset[] }>(
        `/api/v1/brands/${brandId}/assets`,
        DEFAULT_TENANT_ID
      );
      setAssets(assetsResponse.assets || []);
    } catch (error) {
      console.error('Failed to fetch brand detail:', error);
    }
  };

  const handleCreateBrand = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const response = await apiSend(
        '/api/v1/brands',
        'POST',
        {
          name: formData.name,
          description: formData.description,
          website: formData.website,
        },
        DEFAULT_TENANT_ID
      );

      setFormData({ name: '', description: '', website: '' });
      setShowCreateForm(false);
      fetchBrands();
    } catch (error) {
      console.error('Failed to create brand:', error);
    }
  };

  const handleAddAsset = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedBrand) return;

    try {
      await apiSend(
        `/api/v1/brands/${selectedBrand.id}/assets`,
        'POST',
        {
          name: assetData.name,
          asset_type: assetData.asset_type,
          url: assetData.url,
          category: assetData.category,
        },
        DEFAULT_TENANT_ID
      );

      setAssetData({ name: '', asset_type: 'image', url: '', category: 'general' });
      setShowAssetForm(false);
      fetchBrandDetail(selectedBrand.id);
    } catch (error) {
      console.error('Failed to add asset:', error);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Brand Hub</h1>
            <p className="text-sm text-gray-600 mt-1">Multi-brand management and guidelines</p>
          </div>
          <button
            onClick={() => setShowCreateForm(true)}
            className="px-4 py-2 bg-[var(--brand)] text-white rounded-lg hover:bg-[var(--brand)]"
          >
            + New Brand
          </button>
        </div>
      </div>

      <div className="p-6">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Brands List */}
          <div className="lg:col-span-1">
            <div className="bg-white rounded-lg shadow">
              <div className="p-4 border-b border-gray-200">
                <h2 className="text-lg font-semibold text-gray-900">Brands ({brands.length})</h2>
              </div>
              <div className="divide-y max-h-96 overflow-y-auto">
                {brands.map((brand) => (
                  <button
                    key={brand.id}
                    onClick={() => fetchBrandDetail(brand.id)}
                    className={`w-full text-left p-4 transition ${
                      selectedBrand?.id === brand.id ? 'bg-blue-50 border-r-4 border-[var(--brand)]' : 'hover:bg-gray-50'
                    }`}
                  >
                    <div className="font-medium text-gray-900">{brand.name}</div>
                    <div className="text-xs text-gray-600 mt-1">{brand.description}</div>
                    <div className="flex gap-2 mt-2">
                      <span className="text-xs px-2 py-1 bg-gray-100 text-gray-700 rounded">
                        {brand.assets_count} assets
                      </span>
                      <span className="text-xs px-2 py-1 bg-gray-100 text-gray-700 rounded">
                        {brand.team_size} team
                      </span>
                    </div>
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Brand Details */}
          <div className="lg:col-span-2">
            {selectedBrand ? (
              <div className="space-y-6">
                {/* Brand Info */}
                <div className="bg-white rounded-lg shadow p-6">
                  <h3 className="text-lg font-semibold text-gray-900 mb-4">Brand Information</h3>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <label className="text-sm text-gray-600">Name</label>
                      <div className="text-lg font-medium text-gray-900">{selectedBrand.name}</div>
                    </div>
                    <div>
                      <label className="text-sm text-gray-600">Status</label>
                      <div
                        className={`text-lg font-medium capitalize ${
                          selectedBrand.status === 'active' ? 'text-green-600' : 'text-yellow-600'
                        }`}
                      >
                        {selectedBrand.status}
                      </div>
                    </div>
                    <div className="md:col-span-2">
                      <label className="text-sm text-gray-600">Description</label>
                      <div className="text-gray-900">{selectedBrand.description}</div>
                    </div>
                    {selectedBrand.website && (
                      <div className="md:col-span-2">
                        <label className="text-sm text-gray-600">Website</label>
                        <a
                          href={selectedBrand.website}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-[var(--brand)] hover:underline"
                        >
                          {selectedBrand.website}
                        </a>
                      </div>
                    )}
                  </div>
                </div>

                {/* Guidelines */}
                <div className="bg-white rounded-lg shadow p-6">
                  <h3 className="text-lg font-semibold text-gray-900 mb-4">Brand Guidelines</h3>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <label className="text-sm text-gray-600">Primary Color</label>
                      <div className="flex items-center gap-2">
                        <div
                          className="w-12 h-12 rounded border border-gray-300"
                          style={{ backgroundColor: selectedBrand.guidelines.primary_color }}
                        ></div>
                        <span className="font-mono text-sm">{selectedBrand.guidelines.primary_color}</span>
                      </div>
                    </div>
                    <div>
                      <label className="text-sm text-gray-600">Secondary Color</label>
                      <div className="flex items-center gap-2">
                        <div
                          className="w-12 h-12 rounded border border-gray-300"
                          style={{ backgroundColor: selectedBrand.guidelines.secondary_color }}
                        ></div>
                        <span className="font-mono text-sm">{selectedBrand.guidelines.secondary_color}</span>
                      </div>
                    </div>
                    <div className="md:col-span-2">
                      <label className="text-sm text-gray-600">Tone</label>
                      <div className="capitalize text-gray-900">{selectedBrand.guidelines.tone}</div>
                    </div>
                    {selectedBrand.guidelines.required_keywords.length > 0 && (
                      <div className="md:col-span-2">
                        <label className="text-sm text-gray-600">Required Keywords</label>
                        <div className="flex flex-wrap gap-2 mt-1">
                          {selectedBrand.guidelines.required_keywords.map((kw) => (
                            <span key={kw} className="px-2 py-1 bg-green-100 text-green-800 text-xs rounded">
                              {kw}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                    {selectedBrand.guidelines.restricted_keywords.length > 0 && (
                      <div className="md:col-span-2">
                        <label className="text-sm text-gray-600">Restricted Keywords</label>
                        <div className="flex flex-wrap gap-2 mt-1">
                          {selectedBrand.guidelines.restricted_keywords.map((kw) => (
                            <span key={kw} className="px-2 py-1 bg-red-100 text-red-800 text-xs rounded">
                              {kw}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </div>

                {/* Assets */}
                <div className="bg-white rounded-lg shadow p-6">
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="text-lg font-semibold text-gray-900">Asset Library</h3>
                    <button
                      onClick={() => setShowAssetForm(true)}
                      className="px-3 py-1 text-sm bg-[var(--brand)] text-white rounded hover:bg-[var(--brand)]"
                    >
                      + Add Asset
                    </button>
                  </div>

                  {showAssetForm ? (
                    <form onSubmit={handleAddAsset} className="border-t pt-4">
                      <div className="grid grid-cols-2 gap-3 mb-3">
                        <input
                          type="text"
                          placeholder="Asset name"
                          value={assetData.name}
                          onChange={(e) => setAssetData({ ...assetData, name: e.target.value })}
                          className="col-span-2 px-3 py-2 border border-gray-300 rounded text-sm"
                        />
                        <select
                          value={assetData.asset_type}
                          onChange={(e) => setAssetData({ ...assetData, asset_type: e.target.value })}
                          className="px-3 py-2 border border-gray-300 rounded text-sm"
                        >
                          <option value="image">Image</option>
                          <option value="video">Video</option>
                          <option value="template">Template</option>
                        </select>
                        <select
                          value={assetData.category}
                          onChange={(e) => setAssetData({ ...assetData, category: e.target.value })}
                          className="px-3 py-2 border border-gray-300 rounded text-sm"
                        >
                          <option value="general">General</option>
                          <option value="header">Header</option>
                          <option value="product">Product</option>
                        </select>
                        <input
                          type="url"
                          placeholder="Asset URL"
                          value={assetData.url}
                          onChange={(e) => setAssetData({ ...assetData, url: e.target.value })}
                          className="col-span-2 px-3 py-2 border border-gray-300 rounded text-sm"
                        />
                      </div>
                      <div className="flex gap-2">
                        <button
                          type="submit"
                          className="flex-1 px-3 py-2 bg-green-600 text-white text-sm rounded hover:bg-green-700"
                        >
                          Save
                        </button>
                        <button
                          type="button"
                          onClick={() => setShowAssetForm(false)}
                          className="flex-1 px-3 py-2 bg-gray-200 text-gray-900 text-sm rounded hover:bg-gray-300"
                        >
                          Cancel
                        </button>
                      </div>
                    </form>
                  ) : (
                    <div className="space-y-2">
                      {assets.length === 0 ? (
                        <div className="text-center py-6 text-gray-500">No assets yet</div>
                      ) : (
                        assets.map((asset) => (
                          <div key={asset.id} className="p-3 bg-gray-50 rounded flex justify-between items-center">
                            <div>
                              <div className="text-sm font-medium text-gray-900">{asset.name}</div>
                              <div className="text-xs text-gray-600">
                                {asset.type} • {asset.category} • Used {asset.usage_count}x
                              </div>
                            </div>
                            <span className="text-xs text-gray-500">📅 {asset.last_used || 'Never'}</span>
                          </div>
                        ))
                      )}
                    </div>
                  )}
                </div>

                {/* Team */}
                <div className="bg-white rounded-lg shadow p-6">
                  <h3 className="text-lg font-semibold text-gray-900 mb-4">Team</h3>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <label className="text-sm text-gray-600">Owners</label>
                      <div className="mt-2 space-y-1">
                        {selectedBrand.team.owners.map((owner) => (
                          <div key={owner} className="text-sm text-gray-900 px-2 py-1 bg-blue-50 rounded">
                            👤 {owner}
                          </div>
                        ))}
                      </div>
                    </div>
                    <div>
                      <label className="text-sm text-gray-600">Contributors</label>
                      <div className="mt-2 space-y-1">
                        {selectedBrand.team.contributors.map((contributor) => (
                          <div key={contributor} className="text-sm text-gray-900 px-2 py-1 bg-gray-50 rounded">
                            👤 {contributor}
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            ) : (
              <div className="bg-white rounded-lg shadow p-8 text-center">
                <div className="text-[var(--muted)] text-4xl mb-2">📦</div>
                <p className="text-gray-600">Select a brand to view details</p>
              </div>
            )}
          </div>
        </div>

        {/* Create Brand Modal */}
        {showCreateForm && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
            <div className="bg-white rounded-lg shadow-lg max-w-md w-full p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-4">Create New Brand</h2>
              <form onSubmit={handleCreateBrand} className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Brand Name</label>
                  <input
                    type="text"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    required
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
                  <textarea
                    value={formData.description}
                    onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                    rows={3}
                  ></textarea>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Website (Optional)</label>
                  <input
                    type="url"
                    value={formData.website}
                    onChange={(e) => setFormData({ ...formData, website: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                  />
                </div>
                <div className="flex gap-2">
                  <button
                    type="submit"
                    className="flex-1 px-4 py-2 bg-[var(--brand)] text-white rounded-lg hover:bg-[var(--brand)]"
                  >
                    Create
                  </button>
                  <button
                    type="button"
                    onClick={() => setShowCreateForm(false)}
                    className="flex-1 px-4 py-2 bg-gray-200 text-gray-900 rounded-lg hover:bg-gray-300"
                  >
                    Cancel
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
