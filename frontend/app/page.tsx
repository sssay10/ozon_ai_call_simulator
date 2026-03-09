import { headers } from 'next/headers';
import { App } from '@/components/app/app';
import { requireCurrentUser } from '@/lib/auth';
import { getAppConfig } from '@/lib/utils';

export default async function Page() {
  await requireCurrentUser();
  const hdrs = await headers();
  const appConfig = await getAppConfig(hdrs);

  return <App appConfig={appConfig} />;
}
