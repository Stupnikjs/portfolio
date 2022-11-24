import React from 'react';
import profileImg from "../../public/images/PP.png"
import Image from 'next/image';

const PP = () => {
    return (
        <Image className="profilePicture" src={profileImg} alt="profilePicture" />
    );
};

export default PP;