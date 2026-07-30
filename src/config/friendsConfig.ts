import type { FriendLink, FriendsPageConfig } from "../types/friendsConfig";

export const friendsPageConfig: FriendsPageConfig = {
	title: "",
	description: "",
	showCustomContent: false,
	showComment: false,
	randomizeSort: false,
};

export const friendsConfig: FriendLink[] = [];

export const getEnabledFriends = (): FriendLink[] => {
	return friendsConfig.filter((friend) => friend.enabled);
};
