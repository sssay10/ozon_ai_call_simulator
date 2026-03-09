import { NextResponse } from 'next/server';
import { AccessToken, type AccessTokenOptions, type VideoGrant } from 'livekit-server-sdk';
import { RoomConfiguration } from '@livekit/protocol';
import { getCurrentUser } from '@/lib/auth';

type ConnectionDetails = {
  serverUrl: string;
  roomName: string;
  participantName: string;
  participantToken: string;
};

// NOTE: you are expected to define the following environment variables in `.env.local`:
const API_KEY = process.env.LIVEKIT_API_KEY;
const API_SECRET = process.env.LIVEKIT_API_SECRET;
const LIVEKIT_URL = process.env.LIVEKIT_URL;

// don't cache the results
export const revalidate = 0;

export async function POST(req: Request) {
  try {
    if (LIVEKIT_URL === undefined) {
      throw new Error('LIVEKIT_URL is not defined');
    }
    if (API_KEY === undefined) {
      throw new Error('LIVEKIT_API_KEY is not defined');
    }
    if (API_SECRET === undefined) {
      throw new Error('LIVEKIT_API_SECRET is not defined');
    }

    // Parse room config from request body (if provided).
    // Session settings from the UI can be sent as room_config.agents[0].metadata (JSON string).
    const currentUser = await getCurrentUser();
    if (!currentUser) {
      return new NextResponse('Unauthorized', { status: 401 });
    }

    const body = await req.json();
    const roomConfigJson = body?.room_config
      ? {
          ...body.room_config,
          agents: Array.isArray(body.room_config?.agents)
            ? body.room_config.agents.map((agent: Record<string, unknown>) => {
                const rawMetadata =
                  typeof agent.metadata === 'string' && agent.metadata.trim() ? agent.metadata : '{}';
                let parsedMetadata: Record<string, unknown> = {};
                try {
                  const parsed = JSON.parse(rawMetadata);
                  if (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) {
                    parsedMetadata = parsed as Record<string, unknown>;
                  }
                } catch {
                  parsedMetadata = {};
                }

                return {
                  ...agent,
                  metadata: JSON.stringify({
                    ...parsedMetadata,
                    owner_user_id: currentUser.user_id,
                    user_role: currentUser.role,
                    user_email: currentUser.email,
                  }),
                };
              })
            : body.room_config.agents,
        }
      : undefined;
    // Recreate the RoomConfiguration object from JSON object when present.
    const roomConfig = roomConfigJson
      ? RoomConfiguration.fromJson(roomConfigJson, { ignoreUnknownFields: true })
      : undefined;

    // Generate participant token
    const participantName = currentUser.email;
    const participantIdentity = `app_user_${currentUser.user_id}`;
    const roomName = `voice_assistant_room_${Math.floor(Math.random() * 10_000)}`;

    const participantToken = await createParticipantToken(
      {
        identity: participantIdentity,
        name: participantName,
        metadata: JSON.stringify({
          owner_user_id: currentUser.user_id,
          user_role: currentUser.role,
          user_email: currentUser.email,
        }),
      },
      roomName,
      roomConfig
    );

    // Return connection details
    const data: ConnectionDetails = {
      serverUrl: LIVEKIT_URL,
      roomName,
      participantName,
      participantToken,
    };
    const headers = new Headers({
      'Cache-Control': 'no-store',
    });
    return NextResponse.json(data, { headers });
  } catch (error) {
    if (error instanceof Error) {
      console.error(error);
      return new NextResponse(error.message, { status: 500 });
    }
  }
}

function createParticipantToken(
  userInfo: AccessTokenOptions,
  roomName: string,
  roomConfig?: RoomConfiguration
): Promise<string> {
  const at = new AccessToken(API_KEY, API_SECRET, {
    ...userInfo,
    ttl: '15m',
  });
  const grant: VideoGrant = {
    room: roomName,
    roomJoin: true,
    canPublish: true,
    canPublishData: true,
    canSubscribe: true,
  };
  at.addGrant(grant);

  if (roomConfig) {
    at.roomConfig = roomConfig;
  }

  return at.toJwt();
}
