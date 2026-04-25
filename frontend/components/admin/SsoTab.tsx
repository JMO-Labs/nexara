'use client';
/**
 * @file components/admin/SsoTab.tsx
 * @brief OAuth provider management tab for SSO configuration.
 */
import { useState } from 'react';
import {
  useOauthProviders,
  useCreateOauthProvider,
  useToggleOauthProvider,
  useDeleteOauthProvider,
  useDiscoverIssuer,
} from '@/hooks/useAdminOauth';
import Stack from '@mui/joy/Stack';
import Button from '@mui/joy/Button';
import IconButton from '@mui/joy/IconButton';
import Card from '@mui/joy/Card';
import Table from '@mui/joy/Table';
import Typography from '@mui/joy/Typography';
import CircularProgress from '@mui/joy/CircularProgress';
import Alert from '@mui/joy/Alert';
import Modal from '@mui/joy/Modal';
import ModalDialog from '@mui/joy/ModalDialog';
import ModalClose from '@mui/joy/ModalClose';
import Input from '@mui/joy/Input';
import Switch from '@mui/joy/Switch';
import FormControl from '@mui/joy/FormControl';
import FormLabel from '@mui/joy/FormLabel';
import { TrashIcon, PlusIcon } from '@heroicons/react/24/outline';

export function SsoTab() {
  const [openModal, setOpenModal] = useState(false);
  const [issuerUrl, setIssuerUrl] = useState('');
  const [slug, setSlug] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [clientId, setClientId] = useState('');
  const [clientSecret, setClientSecret] = useState('');

  const { data: providers, isLoading, error } = useOauthProviders();
  const createMutation = useCreateOauthProvider();
  const toggleMutation = useToggleOauthProvider();
  const deleteMutation = useDeleteOauthProvider();
  const discoverMutation = useDiscoverIssuer();

  const handleDiscoverIssuer = async () => {
    if (!issuerUrl) return;
    try {
      const discovered = await discoverMutation.mutateAsync(issuerUrl);
      // Auto-fill endpoints based on discovery
      console.log('Discovered endpoints:', discovered);
    } catch (err) {
      console.error('Discovery failed:', err);
    }
  };

  const handleCreateProvider = async (e: React.FormEvent) => {
    e.preventDefault();
    createMutation.mutate({
      slug,
      display_name: displayName,
      provider_type: 'oidc',
      client_id: clientId,
      client_secret: clientSecret,
      issuer: issuerUrl,
    });
    setOpenModal(false);
    setIssuerUrl('');
    setSlug('');
    setDisplayName('');
    setClientId('');
    setClientSecret('');
  };

  if (isLoading) {
    return (
      <Stack alignItems="center" justifyContent="center" sx={{ py: 8 }}>
        <CircularProgress />
      </Stack>
    );
  }

  if (error) {
    return (
      <Alert color="danger" variant="soft">
        Failed to load OAuth providers
      </Alert>
    );
  }

  return (
    <Stack spacing={3}>
      <Stack direction="row" justifyContent="flex-end">
        <Button
          startDecorator={<PlusIcon width={20} height={20} />}
          onClick={() => setOpenModal(true)}
        >
          Add Provider
        </Button>
      </Stack>

      {providers && providers.length > 0 ? (
        <Card variant="outlined">
          <Table
            stripe="odd"
            hoverRow
            sx={{
              '--TableCell-paddingX': '1rem',
              '--TableCell-paddingY': '0.5rem',
            }}
          >
            <thead>
              <tr>
                <th>Name</th>
                <th>Type</th>
                <th>Slug</th>
                <th>Enabled</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {providers.map((provider) => (
                <tr key={provider.id}>
                  <td>
                    <Typography level="body-sm">
                      {provider.display_name}
                    </Typography>
                  </td>
                  <td>
                    <Typography level="body-sm">
                      {provider.provider_type}
                    </Typography>
                  </td>
                  <td>
                    <Typography level="body-sm">{provider.slug}</Typography>
                  </td>
                  <td>
                    <Switch
                      checked={provider.enabled}
                      onChange={() => toggleMutation.mutate(provider.id)}
                    />
                  </td>
                  <td>
                    <IconButton
                      size="sm"
                      variant="soft"
                      color="danger"
                      onClick={() => deleteMutation.mutate(provider.id)}
                      title="Delete provider"
                    >
                      <TrashIcon width={16} height={16} />
                    </IconButton>
                  </td>
                </tr>
              ))}
            </tbody>
          </Table>
        </Card>
      ) : (
        <Alert color="primary" variant="soft">
          No OAuth providers configured yet
        </Alert>
      )}

      <Modal
        aria-labelledby="sso-modal"
        open={openModal}
        onClose={() => setOpenModal(false)}
      >
        <ModalDialog>
          <ModalClose variant="plain" sx={{ m: 1 }} />
          <Typography
            component="h2"
            id="sso-modal"
            level="inherit"
            fontSize="1.25em"
            mb="0.25em"
          >
            Add OAuth Provider
          </Typography>
          <form onSubmit={handleCreateProvider}>
            <Stack spacing={2}>
              <FormControl>
                <FormLabel>Provider Slug</FormLabel>
                <Input
                  value={slug}
                  onChange={(e) => setSlug(e.target.value)}
                  placeholder="e.g., google, github"
                  required
                />
              </FormControl>

              <FormControl>
                <FormLabel>Display Name</FormLabel>
                <Input
                  value={displayName}
                  onChange={(e) => setDisplayName(e.target.value)}
                  placeholder="e.g., Sign in with Google"
                  required
                />
              </FormControl>

              <FormControl>
                <FormLabel>Issuer URL</FormLabel>
                <Input
                  value={issuerUrl}
                  onChange={(e) => setIssuerUrl(e.target.value)}
                  placeholder="https://example.com"
                  type="url"
                  required
                />
                <Button
                  size="sm"
                  variant="soft"
                  onClick={handleDiscoverIssuer}
                  sx={{ mt: 1 }}
                  loading={discoverMutation.isPending}
                >
                  Discover Endpoints
                </Button>
              </FormControl>

              <FormControl>
                <FormLabel>Client ID</FormLabel>
                <Input
                  value={clientId}
                  onChange={(e) => setClientId(e.target.value)}
                  required
                />
              </FormControl>

              <FormControl>
                <FormLabel>Client Secret</FormLabel>
                <Input
                  type="password"
                  value={clientSecret}
                  onChange={(e) => setClientSecret(e.target.value)}
                  required
                />
              </FormControl>

              <Stack direction="row" spacing={2}>
                <Button
                  variant="plain"
                  color="neutral"
                  onClick={() => setOpenModal(false)}
                >
                  Cancel
                </Button>
                <Button
                  type="submit"
                  loading={createMutation.isPending}
                >
                  Create Provider
                </Button>
              </Stack>
            </Stack>
          </form>
        </ModalDialog>
      </Modal>
    </Stack>
  );
}
