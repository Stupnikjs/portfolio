import React from 'react';
import profileImg from "../../public/images/pp_irlande.jpg"
import Image from 'next/image';

const PP = () => {
    return (
        <Image className="profilePicture" src={profileImg} alt="profilePicture" />
    );
};

export default PP;